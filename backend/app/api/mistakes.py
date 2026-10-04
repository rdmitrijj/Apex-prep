from datetime import datetime
from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import select

from app.api.deps import DB, CurrentUser
from app.models import ExamItem, ExamModule, ExamSession, Question, Response
from app.schemas.question import QuestionOut
from app.services import questions as qs

router = APIRouter(tags=["mistakes"])
MissReason = Literal["concept", "careless", "misread", "time", "guess"]


class Mistake(BaseModel):
    response_id: int
    mode: str
    created_at: datetime
    question: QuestionOut
    answer: str | None  # None: left blank in an exam
    key: str
    time_ms: int
    miss_reason: str | None
    explanation: list[str]
    rationales: dict[str, str]


class ReasonIn(BaseModel):
    miss_reason: MissReason | None


@router.get("/mistakes", response_model=list[Mistake])
async def mistakes(
    db: DB,
    user: CurrentUser,
    section: Literal["RW", "MATH"] | None = None,
    skill: str | None = None,
    mode: Literal["exam", "drill", "training"] | None = None,
    reason: MissReason | Literal["untagged"] | None = None,
    limit: int = 100,
) -> list[Mistake]:
    """Missed questions, newest first. Exam misses only count once the exam is over."""
    stmt = (
        select(Response, Question)
        .join(Question, Question.id == Response.question_id)
        .outerjoin(ExamItem, ExamItem.id == Response.exam_item_id)
        .outerjoin(ExamModule, ExamModule.id == ExamItem.module_id)
        .outerjoin(ExamSession, ExamSession.id == ExamModule.session_id)
        .where(Response.user_id == user.id, Response.correct.is_(False))
        .where((Response.exam_item_id.is_(None)) | (ExamSession.status == "completed"))
        .where(ExamItem.pretest.is_not(True))
        .order_by(Response.created_at.desc(), Response.id.desc())
        .limit(max(1, min(limit, 500)))
    )
    if section:
        stmt = stmt.where(Question.skill_id.startswith(section + "."))
    if skill:
        stmt = stmt.where((Question.skill_id == skill) | Question.skill_id.startswith(skill + "."))
    if mode:
        stmt = stmt.where(Response.mode == mode)
    if reason == "untagged":
        stmt = stmt.where(Response.miss_reason.is_(None))
    elif reason:
        stmt = stmt.where(Response.miss_reason == reason)
    names = await qs.skill_names(db)
    return [
        Mistake(
            response_id=r.id,
            mode=r.mode,
            created_at=r.created_at,
            question=qs.public(q, names[q.skill_id]),
            answer=r.answer,
            key=qs.grade(q, "")[1],
            time_ms=r.time_ms,
            miss_reason=r.miss_reason,
            explanation=q.content["explanation"],
            rationales=q.content.get("rationales") or {},
        )
        for r, q in (await db.execute(stmt)).all()
    ]


@router.put("/responses/{response_id}/reason", status_code=204)
async def tag_reason(response_id: int, body: ReasonIn, db: DB, user: CurrentUser) -> None:
    r = await db.get(Response, response_id)
    if r is None or r.user_id != user.id:
        raise HTTPException(404, "Response not found")
    if r.correct is not False:
        raise HTTPException(409, "Only missed questions can be tagged")
    r.miss_reason = body.miss_reason
    await db.commit()
