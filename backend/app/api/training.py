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
from app.engine.weakness import Attempt, Weakness, weakness
from app.models import Question, Response, ReviewSchedule, Skill
from app.schemas.question import QuestionOut
from app.services import questions as qs

router = APIRouter(tags=["training"])
POOL = 8  # training samples among the top-N weaknesses so one session covers several


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


class TrainingQuestion(BaseModel):
    question: QuestionOut
    reasons: list[str]


async def compute(db: AsyncSession, user_id: int) -> list[tuple[Weakness, Skill]]:
    """Every sub-skill with its weakness score, highest first. Uses all graded responses."""
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
        (weakness(s.id, s.section, s.weight, mean[s.section], by_skill.get(s.id, []), s.id in due), s)
        for s in leaves
    ]
    return sorted(out, key=lambda p: p[0].score, reverse=True)


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
        for w, s in (await compute(db, user.id))[: max(1, min(limit, 100))]
    ]


@router.post("/training/next", response_model=TrainingQuestion)
async def next_question(body: TrainingNextIn, db: DB, user: CurrentUser) -> TrainingQuestion:
    ranked = [p for p in await compute(db, user.id) if body.section in (None, p[1].section)]
    pool = ranked[:POOL]
    rng = random.Random(secrets.randbits(64))
    # Weighted by score², so the biggest weaknesses come up most but not exclusively.
    for w, s in rng.choices(pool, weights=[p[0].score ** 2 for p in pool], k=len(pool)) + ranked:
        q = await qs.pick(db, user.id, [s.id], irt.target_difficulty(w.theta), body.exclude_ids)
        if q is not None:
            await db.commit()  # keeps a freshly generated item
            return TrainingQuestion(question=qs.public(q, s.name), reasons=w.reasons)
    raise HTTPException(404, "No questions are available yet")
