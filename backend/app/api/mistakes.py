import re
from datetime import UTC, datetime
from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import select

from app.api.deps import DB, CurrentUser
from app.models import ExamItem, ExamModule, ExamSession, ImportedMistake, Question, Response, Skill
from app.schemas.question import QuestionOut
from app.services import imported
from app.services import questions as qs

router = APIRouter(tags=["mistakes"])
MissReason = Literal["concept", "careless", "misread", "time", "slow", "guess"]


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
    mode: Literal["exam", "drill", "training", "triage"] | None = None,
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


class ImportedOut(BaseModel):
    id: int
    external_id: str
    badge: str  # e.g. "Bluebook PT4"
    source: str
    section: str
    module: int
    question_number: int
    skill_id: str
    skill_name: str
    domain_name: str
    difficulty: str
    result: str
    my_answer: str | None
    correct_answer: str
    summary: str
    lesson: str
    where_to_review: str
    miss_reason: str | None
    twin_ids: list[int]  # question ids of the practice twins, easy to hard
    due: bool
    due_at: datetime
    retired: bool


def _badge(external_id: str) -> str:
    m = re.match(r"bb-pt(\d+)-", external_id)
    return f"Bluebook PT{m.group(1)}" if m else "Official test"


@router.get("/imported-mistakes", response_model=list[ImportedOut])
async def imported_mistakes(db: DB, user: CurrentUser, due: bool = False) -> list[ImportedOut]:
    """Mistakes imported from official practice tests (paraphrases only), in test order."""
    now = datetime.now(UTC)
    stmt = select(ImportedMistake).where(ImportedMistake.user_id == user.id)
    if due:
        stmt = stmt.where(ImportedMistake.retired_at.is_(None), ImportedMistake.due_at <= now)
    rows = (await db.scalars(stmt)).all()
    skills = {s.id: s for s in await db.scalars(select(Skill))}

    def domain(skill_id: str) -> str:
        return skills[".".join(skill_id.split(".")[:2])].name

    section_order = {"RW": 0, "MATH": 1}
    out = [
        ImportedOut(
            id=m.id,
            external_id=m.external_id,
            badge=_badge(m.external_id),
            source=m.source,
            section=skills[m.skill_id].section,
            module=m.module,
            question_number=m.question_number,
            skill_id=m.skill_id,
            skill_name=skills[m.skill_id].name,
            domain_name=domain(m.skill_id),
            difficulty=m.difficulty,
            result=m.result,
            my_answer=m.my_answer,
            correct_answer=m.correct_answer,
            summary=m.summary,
            lesson=m.lesson,
            where_to_review=m.where_to_review,
            miss_reason=m.miss_reason,
            twin_ids=[q.id for q in await imported.twins(db, m)],
            due=m.retired_at is None and m.due_at <= now,
            due_at=m.due_at,
            retired=m.retired_at is not None,
        )
        for m in rows
    ]
    return sorted(out, key=lambda o: (section_order[o.section], o.module, o.question_number))


async def _own(db: DB, user_id: int, mistake_id: int) -> ImportedMistake:
    m = await db.get(ImportedMistake, mistake_id)
    if m is None or m.user_id != user_id:
        raise HTTPException(404, "Mistake not found")
    return m


@router.get("/imported-mistakes/{mistake_id}/twins", response_model=list[QuestionOut])
async def twins(mistake_id: int, db: DB, user: CurrentUser) -> list[QuestionOut]:
    m = await _own(db, user.id, mistake_id)
    names = await qs.skill_names(db)
    return [qs.public(q, names[q.skill_id]) for q in await imported.twins(db, m)]


@router.put("/imported-mistakes/{mistake_id}/reason", status_code=204)
async def tag_imported_reason(mistake_id: int, body: ReasonIn, db: DB, user: CurrentUser) -> None:
    m = await _own(db, user.id, mistake_id)
    m.miss_reason = body.miss_reason
    await db.commit()
