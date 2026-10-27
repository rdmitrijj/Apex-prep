"""Allow responses.mode = 'triage' (the timed triage drill). Widens a check constraint only.

Revision ID: 0007
Revises: 0006
"""

from alembic import op

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


MODES = "mode IN ('exam','drill','training','triage')"


def upgrade() -> None:
    op.drop_constraint(op.f("ck_responses_mode"), "responses", type_="check")
    op.create_check_constraint(op.f("ck_responses_mode"), "responses", MODES)


def downgrade() -> None:
    op.execute("UPDATE responses SET mode = 'drill' WHERE mode = 'triage'")
    op.drop_constraint(op.f("ck_responses_mode"), "responses", type_="check")
    op.create_check_constraint(op.f("ck_responses_mode"), "responses", "mode IN ('exam','drill','training')")
