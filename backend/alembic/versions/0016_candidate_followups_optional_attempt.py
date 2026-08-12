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


def _set_attempt_id_nullable(*, nullable: bool, existing_nullable: bool) -> None:
    """Alter the FK nullability on PostgreSQL and in SQLite test/dev databases."""
    kwargs = {
        "existing_type": sa.String(length=36),
        "existing_nullable": existing_nullable,
        "nullable": nullable,
    }
    if op.get_bind().dialect.name == "sqlite":
        # SQLite cannot execute ``ALTER COLUMN ... DROP/SET NOT NULL`` directly.
        # Alembic batch mode recreates the table while preserving its data and
        # keeps the migration chain executable in local/test SQLite databases.
        with op.batch_alter_table("candidate_followups") as batch_op:
            batch_op.alter_column("attempt_id", **kwargs)
        return
    op.alter_column("candidate_followups", "attempt_id", **kwargs)


def upgrade() -> None:
    _set_attempt_id_nullable(nullable=True, existing_nullable=False)


def downgrade() -> None:
    # A downgrade requires operators to resolve/delete follow-ups that are not
    # linked to an exam attempt before applying this NOT NULL constraint.
    _set_attempt_id_nullable(nullable=False, existing_nullable=True)
