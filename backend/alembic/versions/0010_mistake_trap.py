"""Imported mistakes get the trap that caught the student (PT6 onward). Additive only: one nullable
column.

Revision ID: 0010
Revises: 0009
"""

import sqlalchemy as sa
from alembic import op

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("imported_mistakes", sa.Column("trap", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("imported_mistakes", "trap")
