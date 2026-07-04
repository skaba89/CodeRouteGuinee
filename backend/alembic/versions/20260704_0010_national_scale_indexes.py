"""
Migration 0010 — Index pour le déploiement national (135 centres)

audit_logs est la table à plus forte croissance (chaque login, validation
d'entrée, soumission génère une ligne). Sans index sur (action, created_at),
les endpoints /entries/summary, /supervision/audit-logs et le dashboard
deviennent des full-scans — inacceptable à l'échelle nationale.

Index créés (tous idempotents) :
  audit_logs(action)               — filtres par type d'événement
  audit_logs(created_at)           — fenêtres temporelles (summary 90j)
  audit_logs(action, created_at)   — composite pour /entries/summary
  audit_logs(actor_id)             — traçabilité par utilisateur
  users(email)                     — login (si pas déjà unique-indexé)
  users(center_id)                 — agents par centre
  questions(category)              — tirage d'examen par catégorie

Revision ID: 0010
Revises: 0009
Create Date: 2026-07-04
"""
from __future__ import annotations

from alembic import op
from sqlalchemy import text

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


def _index_exists(connection, index_name: str) -> bool:
    try:
        result = connection.execute(
            text("SELECT indexname FROM pg_indexes WHERE indexname = :n"),
            {"n": index_name},
        ).fetchone()
        return result is not None
    except Exception:
        # SQLite
        try:
            result = connection.execute(
                text("SELECT name FROM sqlite_master WHERE type='index' AND name=:n"),
                {"n": index_name},
            ).fetchone()
            return result is not None
        except Exception:
            return False


def _column_exists(connection, table: str, column: str) -> bool:
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


INDEXES = [
    ("ix_audit_logs_action",             "audit_logs", ["action"]),
    ("ix_audit_logs_created_at",         "audit_logs", ["created_at"]),
    ("ix_audit_logs_action_created_at",  "audit_logs", ["action", "created_at"]),
    ("ix_audit_logs_actor_id",           "audit_logs", ["actor_id"]),
    ("ix_users_center_id",               "users",      ["center_id"]),
    ("ix_questions_category",            "questions",  ["category"]),
]


def upgrade() -> None:
    bind = op.get_bind()
    for index_name, table_name, columns in INDEXES:
        if _index_exists(bind, index_name):
            continue
        # Vérifier que toutes les colonnes existent (schémas historiques variables)
        if not all(_column_exists(bind, table_name, col) for col in columns):
            continue
        op.create_index(index_name, table_name, columns)


def downgrade() -> None:
    bind = op.get_bind()
    for index_name, _table, _cols in INDEXES:
        if _index_exists(bind, index_name):
            op.drop_index(index_name)
