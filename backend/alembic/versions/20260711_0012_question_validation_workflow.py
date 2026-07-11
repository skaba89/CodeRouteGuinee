"""
Migration 0012 — Workflow de validation officielle des questions

Ajoute à la table questions les champs de certification DNTT :
  validation_status : draft | submitted | approved | rejected
  validated_by      : User (DNTT) ayant validé
  validated_at      : horodatage de validation
  rejection_reason  : motif en cas de refus
  version           : numéro de version (traçabilité des modifications)

Rétrocompatible : les questions existantes actives passent 'approved'
pour ne pas bloquer l'examen (elles étaient déjà en service).

Revision ID: 0012
Revises: 0011
Create Date: 2026-07-11
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy import text

revision = "0012"
down_revision = "0011"
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

    if not _col_exists(bind, "questions", "validation_status"):
        op.add_column(
            "questions",
            sa.Column("validation_status", sa.String(20), nullable=False, server_default="draft"),
        )
    if not _col_exists(bind, "questions", "validated_by"):
        op.add_column("questions", sa.Column("validated_by", sa.String(36), nullable=True))
    if not _col_exists(bind, "questions", "validated_at"):
        op.add_column("questions", sa.Column("validated_at", sa.DateTime(), nullable=True))
    if not _col_exists(bind, "questions", "rejection_reason"):
        op.add_column("questions", sa.Column("rejection_reason", sa.Text(), nullable=True))
    if not _col_exists(bind, "questions", "version"):
        op.add_column(
            "questions",
            sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        )

    if not _index_exists(bind, "ix_questions_validation_status"):
        op.create_index("ix_questions_validation_status", "questions", ["validation_status"])

    # Rétrocompatibilité : les questions déjà actives sont considérées
    # comme approuvées (elles étaient déjà en service avant ce workflow).
    bind.execute(text(
        "UPDATE questions SET validation_status = 'approved' "
        "WHERE is_active = :active AND validation_status = 'draft'"
    ), {"active": True})


def downgrade() -> None:
    bind = op.get_bind()
    if _index_exists(bind, "ix_questions_validation_status"):
        op.drop_index("ix_questions_validation_status", table_name="questions")
    for col in ("version", "rejection_reason", "validated_at", "validated_by", "validation_status"):
        if _col_exists(bind, "questions", col):
            op.drop_column("questions", col)
