"""
Migration 0007 — Index manquants + nettoyage

Corrections issues de l'audit :
  1. Index sur exam_attempts (candidate_id, session_id, status, passed, started_at)
  2. Index sur bookings (candidate_id, session_id, status)
  3. Index sur payments (status, created_at) pour les requêtes de dashboard

Revision ID: 0007
Revises: 0006
"""
from __future__ import annotations

from alembic import op

revision      = "0007"
down_revision = "0006"
branch_labels = None
depends_on    = None


def _index_exists(connection, index_name: str) -> bool:
    try:
        result = connection.execute(
            __import__("sqlalchemy").text(
                "SELECT indexname FROM pg_indexes WHERE indexname = :n"
            ),
            {"n": index_name},
        ).fetchone()
        return result is not None
    except Exception:
        # SQLite
        try:
            result = connection.execute(
                __import__("sqlalchemy").text(
                    "SELECT name FROM sqlite_master WHERE type=\'index\' AND name=:n"
                ),
                {"n": index_name},
            ).fetchone()
            return result is not None
        except Exception:
            return False


def upgrade() -> None:
    bind = op.get_bind()

    indexes_to_create = [
        ("ix_exam_attempts_candidate_id", "exam_attempts", ["candidate_id"]),
        ("ix_exam_attempts_session_id",   "exam_attempts", ["session_id"]),
        ("ix_exam_attempts_status",        "exam_attempts", ["status"]),
        ("ix_exam_attempts_passed",        "exam_attempts", ["passed"]),
        ("ix_exam_attempts_started_at",    "exam_attempts", ["started_at"]),
        ("ix_bookings_candidate_id",       "bookings",      ["candidate_id"]),
        ("ix_bookings_session_id",         "bookings",      ["session_id"]),
        ("ix_bookings_status",             "bookings",      ["status"]),
        ("ix_payments_status",             "payments",      ["status"]),
        ("ix_payments_created_at",         "payments",      ["created_at"]),
    ]

    for index_name, table_name, columns in indexes_to_create:
        if not _index_exists(bind, index_name):
            op.create_index(index_name, table_name, columns)


def downgrade() -> None:
    index_names = [
        "ix_exam_attempts_candidate_id", "ix_exam_attempts_session_id",
        "ix_exam_attempts_status", "ix_exam_attempts_passed",
        "ix_exam_attempts_started_at", "ix_bookings_candidate_id",
        "ix_bookings_session_id", "ix_bookings_status",
        "ix_payments_status", "ix_payments_created_at",
    ]
    bind = op.get_bind()
    for name in index_names:
        if _index_exists(bind, name):
            op.drop_index(name)
