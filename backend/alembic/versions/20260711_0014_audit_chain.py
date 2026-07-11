"""
Migration 0014 — Journal d'audit inviolable (chaînage cryptographique)

Ajoute à audit_logs : seq, entry_hash, prev_hash. Permet de chaîner
cryptographiquement les entrées (tamper-evident). Les entrées existantes
restent (seq NULL) ; le chaînage démarre aux nouvelles entrées.

Revision ID: 0014
Revises: 0013
Create Date: 2026-07-11
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy import text

revision = "0014"
down_revision = "0013"
branch_labels = None
depends_on = None


def _col_exists(connection, table: str, column: str) -> bool:
    try:
        result = connection.execute(
            text("SELECT column_name FROM information_schema.columns "
                 "WHERE table_name = :t AND column_name = :c"),
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
    if not _col_exists(bind, "audit_logs", "seq"):
        op.add_column("audit_logs", sa.Column("seq", sa.Integer(), nullable=True))
    if not _col_exists(bind, "audit_logs", "entry_hash"):
        op.add_column("audit_logs", sa.Column("entry_hash", sa.String(64), nullable=True))
    if not _col_exists(bind, "audit_logs", "prev_hash"):
        op.add_column("audit_logs", sa.Column("prev_hash", sa.String(64), nullable=True))
    if not _index_exists(bind, "ix_audit_logs_seq"):
        op.create_index("ix_audit_logs_seq", "audit_logs", ["seq"])


def downgrade() -> None:
    bind = op.get_bind()
    if _index_exists(bind, "ix_audit_logs_seq"):
        op.drop_index("ix_audit_logs_seq", table_name="audit_logs")
    for col in ("prev_hash", "entry_hash", "seq"):
        if _col_exists(bind, "audit_logs", col):
            op.drop_column("audit_logs", col)
