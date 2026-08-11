"""Persist asynchronous provider checkout URLs for safe payment retries.

Revision ID: 0017
Revises: 0016
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0017"
down_revision = "0016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("payments", sa.Column("checkout_url", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("payments", "checkout_url")
