"""PT6 Replay: one twin per Practice Test 6 mistake, served in the original test order
(R&W Module 1, R&W Module 2, Math Module 1, Math Module 2). The order comes from the ids:
pt6-replay-<rw|math>-m<module>-q<number>."""

import re

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Question

REPLAY = re.compile(r"^pt6-replay-(rw|math)-m(\d)-q(\d+)$")


def replay_key(external_id: str) -> tuple[int, int, int]:
    m = REPLAY.match(external_id)
    if m is None:
        raise ValueError(f"not a replay id: {external_id}")
    return (m[1] == "math", int(m[2]), int(m[3]))


async def replay(db: AsyncSession, section: str | None = None) -> list[Question]:
    """Active replay twins in test order; `section` is "rw", "math", or None for both."""
    prefix = f"pt6-replay-{section}-" if section else "pt6-replay-"
    rows = await db.scalars(
        select(Question).where(Question.external_id.like(f"{prefix}%"), Question.status == "active")
    )
    return sorted(
        (q for q in rows if REPLAY.match(q.external_id or "")), key=lambda q: replay_key(q.external_id or "")
    )
