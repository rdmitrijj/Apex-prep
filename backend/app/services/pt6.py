"""PT6 Replay and Twins+: twins of the Practice Test 6 mistakes, served in the original test order
(R&W Module 1, R&W Module 2, Math Module 1, Math Module 2). Ids: pt6-<kind>-<rw|math>-m<module>-q<number>,
kind = replay (mirror twin), twin2 (same difficulty, new surface), twin3 (harder), speed (60-second
version with the first step shown)."""

import re
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Question

KINDS = ("replay", "twin2", "twin3", "speed")
ID = re.compile(r"^pt6-(replay|twin2|twin3|speed)-(rw|math)-m(\d)-q(\d+)$")


def replay_key(external_id: str) -> tuple[int, int, int, int]:
    """Test order; a record's twins stay together (twin 2 before twin 3)."""
    m = ID.match(external_id)
    if m is None:
        raise ValueError(f"not a PT6 twin id: {external_id}")
    return (m[2] == "math", int(m[3]), int(m[4]), KINDS.index(m[1]))


async def replay(
    db: AsyncSession, section: str | None = None, kinds: Sequence[str] = ("replay",)
) -> list[Question]:
    """Active PT6 twins of the given kinds in test order; `section` is "rw", "math", or None for both."""
    rows = await db.scalars(
        select(Question).where(Question.external_id.like("pt6-%"), Question.status == "active")
    )
    out = []
    for q in rows:
        m = ID.match(q.external_id or "")
        if m and m[1] in kinds and section in (None, m[2]):
            out.append(q)
    return sorted(out, key=lambda q: replay_key(q.external_id or ""))
