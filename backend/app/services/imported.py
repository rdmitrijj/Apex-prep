"""Mistakes imported from official practice tests: loading, review schedule, and retirement."""

from datetime import UTC, date, datetime, time
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.engine import srs
from app.models import ImportedMistake, OfficialScore, Question, Response
from app.services import exam as ex

RETIRE_DAYS = 2  # separate days on which every twin was answered correctly
FIELDS = (
    "module",
    "question_number",
    "difficulty",
    "result",
    "my_answer",
    "correct_answer",
    "summary",
    "lesson",
    "where_to_review",
)


async def load(db: AsyncSession, user_id: int, doc: dict[str, Any]) -> dict[str, int]:
    """Idempotent upsert by (user, external_id). Re-running refreshes the text but keeps the review
    schedule and any miss reason the user has changed. Also logs the test's official score once."""
    taken_on = date.fromisoformat(doc["taken_on"])
    existing = {
        m.external_id: m
        for m in await db.scalars(select(ImportedMistake).where(ImportedMistake.user_id == user_id))
    }
    added = 0
    for row in doc["mistakes"]:
        values = {f: row[f] for f in FIELDS} | {
            "source": doc["source"],
            "taken_on": taken_on,
            "skill_id": row["skill"],
            "linked_ids": row["linked_practice_ids"],
        }
        m = existing.get(row["external_id"])
        if m is None:
            m = ImportedMistake(
                user_id=user_id,
                external_id=row["external_id"],
                miss_reason=row.get("miss_reason"),
                due_at=datetime.now(UTC),  # first review: today
                **values,
            )
            db.add(m)
            added += 1
        else:
            for k, v in values.items():
                setattr(m, k, v)
    scored = await db.scalar(
        select(OfficialScore.id).where(
            OfficialScore.user_id == user_id,
            OfficialScore.taken_on == taken_on,
            OfficialScore.label == doc["label"],
        )
    )
    if scored is None and "scores" in doc:
        db.add(
            OfficialScore(
                user_id=user_id,
                taken_on=taken_on,
                kind="practice",
                label=doc["label"],
                rw=doc["scores"]["rw"],
                math=doc["scores"]["math"],
                domain_bars=doc.get("domain_bars"),
            )
        )
        await db.flush()
        await ex.rescore(db, user_id)
    await db.commit()
    return {"mistakes": len(doc["mistakes"]), "added": added, "score_logged": int(scored is None)}


async def twins(db: AsyncSession, m: ImportedMistake) -> list[Question]:
    rows = {
        q.external_id: q
        for q in await db.scalars(
            select(Question).where(Question.external_id.in_(m.linked_ids), Question.status == "active")
        )
    }
    return [rows[e] for e in m.linked_ids if e in rows]


async def retired(db: AsyncSession, user_id: int, m: ImportedMistake) -> bool:
    qs = await twins(db, m)
    if not qs:
        return False
    days: dict[int, set[date]] = {q.id: set() for q in qs}
    for qid, at in await db.execute(
        select(Response.question_id, Response.created_at).where(
            Response.user_id == user_id, Response.question_id.in_(list(days)), Response.correct.is_(True)
        )
    ):
        days[qid].add(at.astimezone(UTC).date())
    return len(set.intersection(*days.values())) >= RETIRE_DAYS


async def on_answer(db: AsyncSession, user_id: int, q: Question, correct: bool) -> None:
    """A graded answer to a twin moves the review schedule of every open mistake it belongs to."""
    if q.external_id is None:
        return
    open_ = (
        await db.scalars(
            select(ImportedMistake).where(
                ImportedMistake.user_id == user_id, ImportedMistake.retired_at.is_(None)
            )
        )
    ).all()
    today = datetime.now(UTC).date()
    await db.flush()  # the new response counts toward retirement
    for m in open_:
        if q.external_id not in m.linked_ids:
            continue
        interval, due = srs.next_review(m.interval_days, m.due_at.date(), today, correct)
        m.interval_days, m.due_at = interval, datetime.combine(due, time(), tzinfo=UTC)
        if correct and await retired(db, user_id, m):
            m.retired_at = datetime.now(UTC)
