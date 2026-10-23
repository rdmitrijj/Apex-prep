import random
import secrets
from collections import Counter
from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import DB, CurrentUser
from app.engine import irt
from app.engine.goals import section_boost
from app.engine.weakness import Attempt, Weakness, weakness
from app.models import ExamItem, ExamModule, ExamSession, Question, Response, ReviewSchedule, Skill, User
from app.schemas.question import QuestionOut
from app.services import questions as qs

router = APIRouter(tags=["training"])
POOL = 8  # training samples among the top-N weaknesses so one session covers several
CLEAR_STREAK = 15  # correct answers in a row (after the exam) that clear a last-exam mistake


class WeaknessOut(BaseModel):
    skill_id: str
    name: str
    section: str
    score: float
    attempts: int
    correct: int
    avg_seconds: float | None
    target_seconds: float
    mastery: float
    reasons: list[str]


class TrainingNextIn(BaseModel):
    exclude_ids: list[int] = Field(default_factory=list, max_length=200)
    section: str | None = Field(default=None, pattern="^(RW|MATH)$")
    last_exam: bool = False  # only sub-skills missed in the latest completed exam and not yet cleared


class ExamMiss(BaseModel):
    skill_id: str
    name: str
    section: str
    missed: int
    streak: int


class ExamMisses(BaseModel):
    exam_id: int | None
    completed_at: datetime | None
    clear_streak: int = CLEAR_STREAK
    open: list[ExamMiss]
    cleared: list[ExamMiss]


class TrainingQuestion(BaseModel):
    question: QuestionOut
    reasons: list[str]


async def compute(db: AsyncSession, user: User) -> list[tuple[Weakness, Skill]]:
    """Every sub-skill with its weakness score, highest first. Uses all graded responses."""
    user_id = user.id
    boost = section_boost(user.section_targets)
    leaves = (await db.scalars(select(Skill).where(Skill.level == "subskill"))).all()
    rows = (
        await db.execute(
            select(Question.skill_id, Question.difficulty_rating, Response)
            .join(Question, Question.id == Response.question_id)
            .where(Response.user_id == user_id, Response.correct.is_not(None))
        )
    ).all()
    now = datetime.now(UTC)
    by_skill: dict[str, list[Attempt]] = {}
    for skill_id, b, r in rows:
        by_skill.setdefault(skill_id, []).append(
            Attempt(
                correct=bool(r.correct),
                b=b,
                time_ms=r.time_ms,
                age_days=(now - r.created_at).total_seconds() / 86400,
                exam=r.mode == "exam",
                eliminated=len(r.eliminated or []),
            )
        )
    n = Counter(s.section for s in leaves)
    mean = {sec: sum(s.weight for s in leaves if s.section == sec) / n[sec] for sec in n}
    due = set(
        await db.scalars(
            select(ReviewSchedule.skill_id).where(
                ReviewSchedule.user_id == user_id, ReviewSchedule.due_at <= now
            )
        )
    )
    out = [
        (
            weakness(
                s.id,
                s.section,
                s.weight,
                mean[s.section],
                by_skill.get(s.id, []),
                s.id in due,
                boost[s.section],
            ),
            s,
        )
        for s in leaves
    ]
    return sorted(out, key=lambda p: p[0].score, reverse=True)


async def exam_misses(db: AsyncSession, user_id: int) -> ExamMisses:
    """Sub-skills missed in the latest completed exam, split by whether they've since been cleared."""
    sess = await db.scalar(
        select(ExamSession)
        .where(ExamSession.user_id == user_id, ExamSession.status == "completed")
        .order_by(ExamSession.completed_at.desc())
        .limit(1)
    )
    if sess is None or sess.completed_at is None:
        return ExamMisses(exam_id=None, completed_at=None, open=[], cleared=[])
    missed = Counter(
        await db.scalars(
            select(Question.skill_id)
            .join(Response, Response.question_id == Question.id)
            .join(ExamItem, ExamItem.id == Response.exam_item_id)
            .join(ExamModule, ExamModule.id == ExamItem.module_id)
            .where(ExamModule.session_id == sess.id, Response.correct.is_(False))
        )
    )
    later = await db.execute(
        select(Question.skill_id, Response.correct)
        .join(Response, Response.question_id == Question.id)
        .where(
            Response.user_id == user_id,
            Response.created_at > sess.completed_at,
            Response.mode != "exam",
            Response.correct.is_not(None),
            Question.skill_id.in_(list(missed)),
        )
        .order_by(Response.created_at, Response.id)
    )
    run: Counter[str] = Counter()
    cleared: set[str] = set()
    for skill_id, ok in later:  # oldest first; once cleared, a skill stays cleared until the next exam
        run[skill_id] = run[skill_id] + 1 if ok else 0
        if run[skill_id] >= CLEAR_STREAK:
            cleared.add(skill_id)
    skills = {s.id: s for s in await db.scalars(select(Skill).where(Skill.id.in_(list(missed))))}
    rows = [
        ExamMiss(
            skill_id=sid,
            name=skills[sid].name,
            section=skills[sid].section,
            missed=n,
            streak=CLEAR_STREAK if sid in cleared else run[sid],
        )
        for sid, n in missed.most_common()
    ]
    return ExamMisses(
        exam_id=sess.id,
        completed_at=sess.completed_at,
        open=[r for r in rows if r.skill_id not in cleared],
        cleared=[r for r in rows if r.skill_id in cleared],
    )


@router.get("/training/exam-misses", response_model=ExamMisses)
async def last_exam_misses(db: DB, user: CurrentUser) -> ExamMisses:
    return await exam_misses(db, user.id)


@router.get("/weaknesses", response_model=list[WeaknessOut])
async def weaknesses(db: DB, user: CurrentUser, limit: int = 10) -> list[WeaknessOut]:
    return [
        WeaknessOut(
            skill_id=w.skill_id,
            name=s.name,
            section=s.section,
            score=round(w.score, 3),
            attempts=w.attempts,
            correct=w.correct,
            avg_seconds=w.avg_seconds,
            target_seconds=w.target_seconds,
            mastery=round(w.mastery, 3),
            reasons=w.reasons,
        )
        for w, s in (await compute(db, user))[: max(1, min(limit, 100))]
    ]


@router.post("/training/next", response_model=TrainingQuestion)
async def next_question(body: TrainingNextIn, db: DB, user: CurrentUser) -> TrainingQuestion:
    ranked = [p for p in await compute(db, user) if body.section in (None, p[1].section)]
    if body.last_exam:
        todo = {m.skill_id for m in (await exam_misses(db, user.id)).open}
        ranked = [p for p in ranked if p[1].id in todo]
        if not ranked:
            raise HTTPException(404, "No open mistakes from your last exam")
    pool = ranked[:POOL]
    rng = random.Random(secrets.randbits(64))
    # Weighted by score², so the biggest weaknesses come up most but not exclusively.
    for w, s in rng.choices(pool, weights=[p[0].score ** 2 for p in pool], k=len(pool)) + ranked:
        q = await qs.pick(db, user.id, [s.id], irt.target_difficulty(w.theta), body.exclude_ids)
        if q is not None:
            await db.commit()  # keeps a freshly generated item
            return TrainingQuestion(question=qs.public(q, s.name), reasons=w.reasons)
    raise HTTPException(404, "No questions are available yet")
