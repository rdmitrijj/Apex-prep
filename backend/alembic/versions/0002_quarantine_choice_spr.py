"""Quarantine generated SPR items whose stem refers to answer choices ("Which of the following ...").

Revision ID: 0002
Revises: 0001
"""

from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE questions SET status = 'quarantined'
        WHERE format = 'spr' AND source = 'generator'
          AND content->>'stem' ~* '\\mwhich (of the following|choice|option)\\M'
        """
    )


def downgrade() -> None:
    pass  # data cleanup only; quarantined items stay out of rotation
