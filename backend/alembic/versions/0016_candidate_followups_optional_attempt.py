"""Allow candidate follow-ups that are not tied to an exam attempt.

Revision ID: 0016
Revises: 0015
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0016"
down_revision = "0015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "candidate_followups",
        "attempt_id",
        existing_type=sa.String(length=36),
        existing_nullable=False,
        nullable=True,
    )


def downgrade() -> None:
    # A downgrade requires operators to resolve/delete follow-ups that are not
    # linked to an exam attempt before applying this NOT NULL constraint.
    op.alter_column(
        "candidate_followups",
        "attempt_id",
        existing_type=sa.String(length=36),
        existing_nullable=True,
        nullable=False,
    )
