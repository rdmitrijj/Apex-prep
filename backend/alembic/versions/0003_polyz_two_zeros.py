"""Quarantine generated "which is a zero of f" items that offered two zeros, and regrade those answers.

Revision ID: 0003
Revises: 0002
"""

import json
import re

import sqlalchemy as sa
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    rows = conn.execute(
        sa.text(
            "SELECT id, content FROM questions WHERE skill_id = 'MATH.ADV.NLF.POLYZ' "
            "AND source = 'generator' AND format = 'mc' AND difficulty = 'easy'"
        )
    ).all()
    for qid, content in rows:
        c = content if isinstance(content, dict) else json.loads(content)
        zeros = {-int(sign + n) for sign, n in re.findall(r"\(x ([+-]) (\d+)\)", c["stem"])}
        right = [
            letter for letter, ch in zip("ABCD", c["choices"], strict=True) if int(ch.strip("$")) in zeros
        ]
        if len(right) < 2:
            continue
        conn.execute(sa.text("UPDATE questions SET status = 'quarantined' WHERE id = :id"), {"id": qid})
        # A zero is a right answer to "which is a zero of f", whichever letter the generator keyed.
        conn.execute(
            sa.text(
                "UPDATE responses SET correct = true, miss_reason = NULL "
                "WHERE question_id = :id AND answer = ANY(:letters) AND correct = false"
            ),
            {"id": qid, "letters": right},
        )


def downgrade() -> None:
    pass  # data cleanup only
