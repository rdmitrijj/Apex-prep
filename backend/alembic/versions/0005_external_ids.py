"""Stable seed keys (questions.external_id) and imported official-test mistakes. Additive only.

Existing seed rows get their key from 0005_seed_ids.json (content hash -> id, taken before any
item was edited), so later edits update those rows in place and keep every answer linked.

Revision ID: 0005
Revises: 0004
"""

import json
from pathlib import Path

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None

JSONB = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")


def upgrade() -> None:
    op.add_column("questions", sa.Column("external_id", sa.String(64), nullable=True))
    op.create_unique_constraint(op.f("uq_questions_external_id"), "questions", ["external_id"])
    ids = json.loads((Path(__file__).with_name("0005_seed_ids.json")).read_text())
    op.get_bind().execute(
        sa.text("UPDATE questions SET external_id = :id WHERE content_hash = :h AND external_id IS NULL"),
        [{"h": h, "id": i} for h, i in ids.items()],
    )
    op.create_table(
        "imported_mistakes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("external_id", sa.String(64), nullable=False),
        sa.Column("source", sa.String(120), nullable=False),
        sa.Column("taken_on", sa.Date(), nullable=False),
        sa.Column("module", sa.SmallInteger(), nullable=False),
        sa.Column("question_number", sa.SmallInteger(), nullable=False),
        sa.Column("skill_id", sa.String(64), nullable=False),
        sa.Column("difficulty", sa.String(6), nullable=False),
        sa.Column("result", sa.String(9), nullable=False),
        sa.Column("my_answer", sa.String(120), nullable=True),
        sa.Column("correct_answer", sa.String(120), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("lesson", sa.Text(), nullable=False),
        sa.Column("where_to_review", sa.String(200), nullable=False),
        sa.Column("miss_reason", sa.String(16), nullable=True),
        sa.Column("linked_ids", JSONB, server_default="[]", nullable=False),
        sa.Column("interval_days", sa.SmallInteger(), nullable=True),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("retired_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("result IN ('incorrect','omitted')", name=op.f("ck_imported_mistakes_result")),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_imported_mistakes_user_id_users"), ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["skill_id"], ["skills.id"], name=op.f("fk_imported_mistakes_skill_id_skills")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_imported_mistakes")),
        sa.UniqueConstraint("user_id", "external_id", name=op.f("uq_imported_mistakes_user_id")),
    )


def downgrade() -> None:
    op.drop_table("imported_mistakes")
    op.drop_constraint(op.f("uq_questions_external_id"), "questions", type_="unique")
    op.drop_column("questions", "external_id")
