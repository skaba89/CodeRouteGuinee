"""
Migration 0008 — users.center_id

Ajoute la colonne center_id sur la table users pour associer
les agents 'center' à leur centre d'appartenance.
Résout le cross-center data leak identifié en audit.

Revision ID: 0008
Revises: 0007
Create Date: 2026-06-25
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision      = "0008"
down_revision = "0007"
branch_labels = None
depends_on    = None


def _col_exists(connection, table: str, col: str) -> bool:
    try:
        result = connection.execute(
            sa.text("SELECT column_name FROM information_schema.columns "
                    "WHERE table_name=:t AND column_name=:c"),
            {"t": table, "c": col},
        ).fetchone()
        return result is not None
    except Exception:
        try:
            rows = connection.execute(sa.text(f"PRAGMA table_info({table})")).fetchall()  # noqa: S608
            return any(r[1] == col for r in rows)
        except Exception:
            return False


def upgrade() -> None:
    bind = op.get_bind()
    if not _col_exists(bind, "users", "center_id"):
        op.add_column(
            "users",
            sa.Column("center_id", sa.String(36), nullable=True, index=True),
        )


def downgrade() -> None:
    bind = op.get_bind()
    if _col_exists(bind, "users", "center_id"):
        op.drop_column("users", "center_id")
