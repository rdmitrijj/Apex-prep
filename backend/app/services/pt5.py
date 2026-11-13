"""PT5 Weakness Drill: set definitions and rule cards (seed/pt5), per-user set progress, and the
review schedule of mastered sets."""

import json
from datetime import UTC, date, datetime, time
from functools import cache
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.engine import srs
from app.engine import weakset as ws
from app.models import Question, Response, SetReview
from app.services.questions import SEED_DIR

DIR = SEED_DIR / "pt5"


@cache
def sets() -> dict[str, dict[str, Any]]:
    return {s["id"]: s for s in json.loads((DIR / "sets.json").read_text())["sets"]}


@cache
def rule(set_id: str) -> str:
    path = DIR / "rules" / f"{set_id}.md"
    return path.read_text() if path.exists() else ""


@cache
def plan() -> dict[str, Any]:
    out: dict[str, Any] = json.loads((DIR / "plan.json").read_text())
    return out


@cache
def forms() -> dict[str, dict[str, list[str]]]:
    path = DIR / "forms.json"
    return json.loads(path.read_text()) if path.exists() else {}


def default_reason(q: Question) -> str | None:
    """The set's usual miss reason, pre-filled on a wrong answer to a drill-set question."""
    set_id = ws.set_of(q.external_id)
    return sets()[set_id]["miss_reason"] if set_id in sets() else None


async def history(
    db: AsyncSession, user_id: int, set_id: str | None = None
) -> dict[str, list[tuple[date, bool]]]:
    """Graded answers (any mode) on drill-set questions, per set, oldest first."""
    like = f"pt5-{set_id}-%" if set_id else "pt5-%"
    rows = await db.execute(
        select(Question.external_id, Response.created_at, Response.correct)
        .join(Question, Question.id == Response.question_id)
        .where(Response.user_id == user_id, Response.correct.is_not(None), Question.external_id.like(like))
        .order_by(Response.created_at, Response.id)
    )
    out: dict[str, list[tuple[date, bool]]] = {}
    for eid, at, correct in rows:
        s = ws.set_of(eid)
        if s is not None:
            out.setdefault(s, []).append((at.astimezone(UTC).date(), bool(correct)))
    return out


async def on_answer(db: AsyncSession, user_id: int, q: Question, correct: bool) -> None:
    """After a graded answer: schedule the set's first review once it is mastered, then move that
    schedule on every later answer (a miss resets it to 1 day)."""
    set_id = ws.set_of(q.external_id)
    if set_id is None:
        return
    today = datetime.now(UTC).date()
    row = await db.get(SetReview, (user_id, set_id))
    if row is not None:
        interval, due = srs.next_review(row.interval_days, row.due_at.date(), today, correct)
        row.interval_days, row.due_at = interval, datetime.combine(due, time(), tzinfo=UTC)
        return
    await db.flush()  # the new response counts
    if ws.status((await history(db, user_id, set_id)).get(set_id, [])).mastered:
        interval, due = srs.next_review(None, None, today, True)
        db.add(
            SetReview(
                user_id=user_id,
                set_id=set_id,
                mastered_at=datetime.now(UTC),
                interval_days=interval,
                due_at=datetime.combine(due, time(), tzinfo=UTC),
            )
        )
