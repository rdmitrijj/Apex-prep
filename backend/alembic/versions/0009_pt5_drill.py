"""PT5 Weakness Drill: set review schedules, plan checklist, 'guessed' imported results, longer
Triage mode names (Mini Mock). Additive only: two new tables, one widened check, one wider column.

Revision ID: 0009
Revises: 0008
"""

import sqlalchemy as sa
from alembic import op

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint(op.f("ck_imported_mistakes_result"), "imported_mistakes", type_="check")
    op.create_check_constraint(
        op.f("ck_imported_mistakes_result"),
        "imported_mistakes",
        "result IN ('incorrect','omitted','guessed')",
    )
    op.alter_column("triage_sessions", "mode", type_=sa.String(16), existing_type=sa.String(8))
    op.create_table(
        "set_reviews",
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("set_id", sa.String(length=32), nullable=False),
        sa.Column("mastered_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("interval_days", sa.SmallInteger(), nullable=False),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_set_reviews_user_id_users"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("user_id", "set_id", name=op.f("pk_set_reviews")),
    )
    op.create_table(
        "plan_checks",
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("item_key", sa.String(length=64), nullable=False),
        sa.Column("done_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_plan_checks_user_id_users"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("user_id", "item_key", name=op.f("pk_plan_checks")),
    )


def downgrade() -> None:
    op.drop_table("plan_checks")
    op.drop_table("set_reviews")
    op.execute("UPDATE triage_sessions SET mode = left(mode, 8)")
    op.alter_column("triage_sessions", "mode", type_=sa.String(8), existing_type=sa.String(16))
    op.execute("DELETE FROM imported_mistakes WHERE result = 'guessed'")
    op.drop_constraint(op.f("ck_imported_mistakes_result"), "imported_mistakes", type_="check")
    op.create_check_constraint(
        op.f("ck_imported_mistakes_result"), "imported_mistakes", "result IN ('incorrect','omitted')"
    )
