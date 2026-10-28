"""Finished Triage drills (history chart). Additive only: one new table.

Revision ID: 0008
Revises: 0007
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "triage_sessions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("mode", sa.String(length=8), nullable=False),
        sa.Column("limit_s", sa.Integer(), nullable=False),
        sa.Column("elapsed_ms", sa.Integer(), nullable=False),
        sa.Column("total", sa.SmallInteger(), nullable=False),
        sa.Column("correct", sa.SmallInteger(), nullable=False),
        sa.Column("blanks", sa.SmallInteger(), nullable=False),
        sa.Column("avg_seconds", sa.Float(), nullable=False),
        sa.Column("items", sa.JSON().with_variant(postgresql.JSONB(), "postgresql"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_triage_sessions_user_id_users"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_triage_sessions")),
    )
    op.create_index(op.f("ix_triage_sessions_user_id"), "triage_sessions", ["user_id"])


def downgrade() -> None:
    op.drop_index(op.f("ix_triage_sessions_user_id"), table_name="triage_sessions")
    op.drop_table("triage_sessions")
