"""
Migration 0013 — Traductions multilingues des questions

Ajoute questions.translations (JSON) : contenu traduit dans les langues
nationales guinéennes (Pular, Malinké, Soussou, etc.). Le français reste
la source de référence ; les langues absentes retombent sur le français.

Revision ID: 0013
Revises: 0012
Create Date: 2026-07-11
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy import text

revision = "0013"
down_revision = "0012"
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


def upgrade() -> None:
    bind = op.get_bind()
    if not _col_exists(bind, "questions", "translations"):
        op.add_column("questions", sa.Column("translations", sa.JSON(), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    if _col_exists(bind, "questions", "translations"):
        op.drop_column("questions", "translations")
