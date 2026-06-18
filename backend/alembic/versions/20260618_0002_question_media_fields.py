"""Add media fields to exam questions.

Revision ID: 20260618_0002
Revises: 20260617_0001
Create Date: 2026-06-18
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20260618_0002"
down_revision: Union[str, None] = "20260617_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("questions", sa.Column("media_type", sa.String(length=20), nullable=True))
    op.add_column("questions", sa.Column("media_url", sa.Text(), nullable=True))
    op.add_column("questions", sa.Column("media_alt", sa.String(length=255), nullable=True))


def downgrade() -> None:
    op.drop_column("questions", "media_alt")
    op.drop_column("questions", "media_url")
    op.drop_column("questions", "media_type")
