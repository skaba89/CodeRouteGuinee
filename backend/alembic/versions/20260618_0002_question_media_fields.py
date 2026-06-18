"""Add media fields to exam questions.

Revision ID: 20260618_0002
Revises: 20260617_0001
Create Date: 2026-06-18
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision: str = "20260618_0002"
down_revision: Union[str, None] = "20260617_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    existing_columns = {column["name"] for column in inspect(op.get_bind()).get_columns("questions")}
    if "media_type" not in existing_columns:
        op.add_column("questions", sa.Column("media_type", sa.String(length=20), nullable=True))
    if "media_url" not in existing_columns:
        op.add_column("questions", sa.Column("media_url", sa.Text(), nullable=True))
    if "media_alt" not in existing_columns:
        op.add_column("questions", sa.Column("media_alt", sa.String(length=255), nullable=True))


def downgrade() -> None:
    existing_columns = {column["name"] for column in inspect(op.get_bind()).get_columns("questions")}
    if "media_alt" in existing_columns:
        op.drop_column("questions", "media_alt")
    if "media_url" in existing_columns:
        op.drop_column("questions", "media_url")
    if "media_type" in existing_columns:
        op.drop_column("questions", "media_type")
