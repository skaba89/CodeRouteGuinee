"""
Migration 0011 — Inscription candidat libre et auto-école

candidates.user_id       : compte User du candidat (auto-inscription libre)
candidates.registered_by : User auto-école ayant inscrit le candidat

Revision ID: 0011
Revises: 0010
Create Date: 2026-07-04
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy import text

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None


def _col_exists(connection, table: str, column: str) -> bool:
    try:
        result = connection.execute(
            text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name = :t AND column_name = :c"
            ),
            {"t": table, "c": column},
        ).fetchone()
        return result is not None
    except Exception:
        try:
            rows = connection.execute(text(f"PRAGMA table_info({table})")).fetchall()
            return any(r[1] == column for r in rows)
        except Exception:
            return False


def _index_exists(connection, name: str) -> bool:
    try:
        return connection.execute(
            text("SELECT indexname FROM pg_indexes WHERE indexname = :n"), {"n": name}
        ).fetchone() is not None
    except Exception:
        try:
            return connection.execute(
                text("SELECT name FROM sqlite_master WHERE type='index' AND name=:n"),
                {"n": name},
            ).fetchone() is not None
        except Exception:
            return False


def upgrade() -> None:
    bind = op.get_bind()
    if not _col_exists(bind, "candidates", "user_id"):
        op.add_column("candidates", sa.Column("user_id", sa.String(36), nullable=True))
    if not _col_exists(bind, "candidates", "registered_by"):
        op.add_column("candidates", sa.Column("registered_by", sa.String(36), nullable=True))
    if not _index_exists(bind, "ix_candidates_user_id"):
        op.create_index("ix_candidates_user_id", "candidates", ["user_id"])
    if not _index_exists(bind, "ix_candidates_registered_by"):
        op.create_index("ix_candidates_registered_by", "candidates", ["registered_by"])


def downgrade() -> None:
    bind = op.get_bind()
    if _index_exists(bind, "ix_candidates_registered_by"):
        op.drop_index("ix_candidates_registered_by")
    if _index_exists(bind, "ix_candidates_user_id"):
        op.drop_index("ix_candidates_user_id")
    if _col_exists(bind, "candidates", "registered_by"):
        op.drop_column("candidates", "registered_by")
    if _col_exists(bind, "candidates", "user_id"):
        op.drop_column("candidates", "user_id")
