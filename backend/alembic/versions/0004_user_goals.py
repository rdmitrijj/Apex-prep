"""Per-user score goals; existing accounts keep the original targets (1350 total, 700 Math, 5 Dec 2026).

Revision ID: 0004
Revises: 0003
"""

import sqlalchemy as sa
from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    for col in ("target_total", "target_math", "target_rw"):
        op.add_column("users", sa.Column(col, sa.SmallInteger(), nullable=True))
    op.execute(
        "UPDATE users SET target_total = 1350, target_math = 700, "
        "test_date = COALESCE(test_date, DATE '2026-12-05')"
    )


def downgrade() -> None:
    for col in ("target_rw", "target_math", "target_total"):
        op.drop_column("users", col)
