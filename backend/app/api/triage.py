import random
import secrets
from datetime import datetime
from typing import Any, Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.api.deps import DB, CurrentUser
from app.api.training import compute
from app.engine import exam as bp
from app.engine import triage as tr
from app.generators.spr import is_valid_entry
from app.models import Question, Response, TriageSession
from app.schemas.question import QuestionOut
from app.services import imported
from app.services import questions as qs

router = APIRouter(prefix="/triage", tags=["triage"])
Mode = Literal["sprint", "module", "weakness", "math"]


class StartIn(BaseModel):
    mode: Mode


class TriageQuestion(BaseModel):
    question: QuestionOut
    target_seconds: int


class StartOut(BaseModel):
    mode: Mode
    limit_seconds: int
    questions: list[TriageQuestion]


class ItemIn(BaseModel):
    question_id: int
    answer: str | None = Field(default=None, max_length=16)  # None: left blank
    time_ms: int = Field(ge=0, le=3_600_000)
    flagged: bool = False
    first_pass: bool = True  # the final answer was given on the first visit
    eliminated: list[Literal["A", "B", "C", "D"]] = Field(default_factory=list, max_length=4)


class SubmitIn(BaseModel):
    mode: Mode
    elapsed_ms: int = Field(ge=0, le=3_600_000)
    items: list[ItemIn] = Field(min_length=1, max_length=30)


class GroupOut(BaseModel):
    id: str
    name: str
    total: int
    correct: int
    avg_seconds: float
    target_seconds: float


class SinkOut(BaseModel):
    skill_id: str
    name: str
    count: int


class ItemResult(BaseModel):
    response_id: int
    question: QuestionOut
    answer: str | None
    key: str
    correct: bool
    seconds: float
    target_seconds: int
    time_sink: bool
    flagged: bool
    first_pass: bool
    explanation: list[str]
    rationales: dict[str, str]
    vocab: list[dict[str, Any]]


class SessionSummary(BaseModel):
    id: int
    mode: str
    created_at: datetime
    limit_seconds: int
    elapsed_seconds: float
    total: int
    correct: int
    blanks: int
    avg_seconds: float


class Results(SessionSummary):
    by_domain: list[GroupOut]
    by_skill: list[GroupOut]
    time_sinks: list[SinkOut]
    first_pass: tuple[int, int]
    second_pass: tuple[int, int]
    recommendations: list[str]
    items: list[ItemResult]


async def weak_skills(db: DB, user: CurrentUser) -> list[str]:
    """R&W skills ordered by their weakest sub-skill's score (error rate, recency, imported misses)."""
    best: dict[str, float] = {}
    for w, s in await compute(db, user):
        if s.section == "RW":
            k = tr.skill_of(s.id)
            best[k] = max(best.get(k, 0.0), w.score)
    return sorted(best, key=lambda k: -best[k])


@router.post("/start", response_model=StartOut)
async def start(body: StartIn, db: DB, user: CurrentUser) -> StartOut:
    rng = random.Random(secrets.randbits(64))
    weak = await weak_skills(db, user) if body.mode == "weakness" else []
    picked: list[Question] = []
    for slot in tr.plan(body.mode, weak, rng):
        leaves = await qs.leaves_under(db, [slot.prefix])
        q = await qs.pick(db, user.id, leaves, slot.difficulty, [p.id for p in picked])
        if q is None:
            raise HTTPException(409, "Not enough questions for this mode yet")
        picked.append(q)
    if body.mode == "module":  # official order: by domain, grouped by skill, easier first
        order = bp.order("RW", [(q.skill_id, q.difficulty_rating) for q in picked], rng)
        picked = [picked[i] for i in order]
    else:
        rng.shuffle(picked)
    await db.commit()  # keeps freshly generated math items
    names = await qs.skill_names(db)
    return StartOut(
        mode=body.mode,
        limit_seconds=tr.MODES[body.mode][1],
        questions=[
            TriageQuestion(
                question=qs.public(q, names[q.skill_id]), target_seconds=tr.target_seconds(q.skill_id)
            )
            for q in picked
        ],
    )


@router.post("/sessions", response_model=Results)
async def submit(body: SubmitIn, db: DB, user: CurrentUser) -> Results:
    """Grade a finished drill. Every question becomes a response (blanks count as wrong), so misses
    reach the Mistake Notebook and review schedule; blanks and slow misses are tagged 'slow'."""
    ids = [i.question_id for i in body.items]
    if len(set(ids)) != len(ids):
        raise HTTPException(422, "Duplicate question")
    questions = {q.id: q for q in await db.scalars(select(Question).where(Question.id.in_(ids)))}
    if len(questions) != len(ids):
        raise HTTPException(404, "Question not found")
    names = await qs.skill_names(db)
    graded: list[tuple[ItemIn, Question, Response, tr.Item]] = []
    for it in body.items:
        q = questions[it.question_id]
        answer = (
            it.answer.strip().upper() if it.answer and q.format == "mc" else (it.answer or "").strip() or None
        )
        if answer is not None and not (
            answer in ("A", "B", "C", "D") if q.format == "mc" else is_valid_entry(answer)
        ):
            raise HTTPException(422, "Invalid answer format")
        correct = answer is not None and qs.grade(q, answer)[0]
        item = tr.Item(q.skill_id, correct, answer is None, it.time_ms / 1000, it.first_pass)
        r = Response(
            user_id=user.id,
            question_id=q.id,
            mode="triage",
            answer=answer,
            correct=correct,
            time_ms=it.time_ms,
            flagged=it.flagged,
            eliminated=list(it.eliminated),
            miss_reason="slow" if answer is None or tr.is_time_sink(item) else None,
        )
        db.add(r)
        await qs.record_review(db, user.id, q.skill_id, correct)
        await imported.on_answer(db, user.id, q, correct)
        graded.append((it, q, r, item))
    a = tr.analyze([g[3] for g in graded], names)
    await db.flush()
    sess = TriageSession(
        user_id=user.id,
        mode=body.mode,
        limit_s=tr.MODES[body.mode][1],
        elapsed_ms=body.elapsed_ms,
        total=a.total,
        correct=a.correct,
        blanks=a.blanks,
        avg_seconds=a.avg_seconds,
        items=[
            {
                "question_id": q.id,
                "response_id": r.id,
                "answer": r.answer,
                "time_ms": it.time_ms,
                "flagged": it.flagged,
                "first_pass": it.first_pass,
            }
            for it, q, r, _ in graded
        ],
    )
    db.add(sess)
    await db.commit()
    await db.refresh(sess, ["created_at"])
    group = lambda g: GroupOut(name=names.get(g.id, g.id), **vars(g))  # noqa: E731
    return Results(
        **_summary(sess).model_dump(),
        by_domain=[group(g) for g in a.by_domain],
        by_skill=[group(g) for g in a.by_skill],
        time_sinks=[SinkOut(skill_id=k, name=names.get(k, k), count=n) for k, n in a.time_sinks.items()],
        first_pass=a.first_pass,
        second_pass=a.second_pass,
        recommendations=a.recommendations,
        items=[
            ItemResult(
                response_id=r.id,
                question=qs.public(q, names[q.skill_id]),
                answer=r.answer,
                key=qs.grade(q, "")[1],
                correct=item.correct,
                seconds=item.seconds,
                target_seconds=tr.target_seconds(q.skill_id),
                time_sink=tr.is_time_sink(item),
                flagged=it.flagged,
                first_pass=it.first_pass,
                explanation=q.content["explanation"],
                rationales=q.content.get("rationales") or {},
                vocab=q.content.get("vocab") or [],
            )
            for it, q, r, item in graded
        ],
    )


def _summary(s: TriageSession) -> SessionSummary:
    return SessionSummary(
        id=s.id,
        mode=s.mode,
        created_at=s.created_at,
        limit_seconds=s.limit_s,
        elapsed_seconds=s.elapsed_ms / 1000,
        total=s.total,
        correct=s.correct,
        blanks=s.blanks,
        avg_seconds=s.avg_seconds,
    )


@router.get("/sessions", response_model=list[SessionSummary])
async def history(db: DB, user: CurrentUser) -> list[SessionSummary]:
    rows = await db.scalars(
        select(TriageSession).where(TriageSession.user_id == user.id).order_by(TriageSession.created_at)
    )
    return [_summary(s) for s in rows]
