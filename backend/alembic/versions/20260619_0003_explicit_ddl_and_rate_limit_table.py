"""Explicit DDL for all tables + login_rate_limit table.

Remplace la migration 0001 (create_all) par un DDL explicite et idempotent.
Ajoute également la table login_rate_limit pour le rate limiter persistant.

Revision ID: 20260619_0003
Revises: 20260618_0002
Create Date: 2026-06-19
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260619_0003"
down_revision: Union[str, None] = "20260618_0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_exists(table_name: str) -> bool:
    bind = op.get_bind()
    return sa.inspect(bind).has_table(table_name)


def upgrade() -> None:
    # ── Tables de base (idempotentes — ignorées si déjà présentes) ─────────

    # Table rate limit persistant (nouvelle table, pas dans la migration 0001)
    if not _table_exists("login_rate_limit"):
        op.create_table(
            "login_rate_limit",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("key", sa.String(length=255), nullable=False),
            sa.Column("attempted_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            "idx_login_rate_limit_key_time",
            "login_rate_limit",
            ["key", "attempted_at"],
        )

    # ── Colonnes ajoutées depuis migration 0001 ─────────────────────────────
    # Vérification idempotente pour chaque colonne ajoutée après le schéma initial

    bind = op.get_bind()
    insp = sa.inspect(bind)

    # exam_attempts — colonne passed ajoutée en phase 2 si absente
    if _table_exists("exam_attempts"):
        existing = {col["name"] for col in insp.get_columns("exam_attempts")}
        if "passed" not in existing:
            op.add_column("exam_attempts", sa.Column("passed", sa.Boolean(), nullable=True))
        if "score" not in existing:
            op.add_column("exam_attempts", sa.Column("score", sa.Integer(), nullable=True))

    # device_sessions — colonne risk_reason
    if _table_exists("device_sessions"):
        existing = {col["name"] for col in insp.get_columns("device_sessions")}
        if "risk_reason" not in existing:
            op.add_column("device_sessions", sa.Column("risk_reason", sa.Text(), nullable=True))
        if "last_seen_at" not in existing:
            op.add_column("device_sessions", sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True))

    # exam_question_traces — colonne selection_mode
    if _table_exists("exam_question_traces"):
        existing = {col["name"] for col in insp.get_columns("exam_question_traces")}
        if "selection_mode" not in existing:
            op.add_column("exam_question_traces", sa.Column("selection_mode", sa.String(length=50), nullable=True))
        if "version_label" not in existing:
            op.add_column("exam_question_traces", sa.Column("version_label", sa.String(length=120), nullable=True))

    # center_incidents — colonnes new_attempt_id
    if _table_exists("center_incidents"):
        existing = {col["name"] for col in insp.get_columns("center_incidents")}
        if "new_attempt_id" not in existing:
            op.add_column("center_incidents", sa.Column("new_attempt_id", sa.String(length=36), nullable=True))

    # payments — colonne receipt_number
    if _table_exists("payments"):
        existing = {col["name"] for col in insp.get_columns("payments")}
        if "receipt_number" not in existing:
            op.add_column("payments", sa.Column("receipt_number", sa.String(length=80), nullable=True))
        if "official_import" not in existing:
            op.add_column("payments", sa.Column("official_import", sa.Boolean(), server_default="false", nullable=True))

    # exam_monitoring_events — colonne risk_score
    if _table_exists("exam_monitoring_events"):
        existing = {col["name"] for col in insp.get_columns("exam_monitoring_events")}
        if "risk_score" not in existing:
            op.add_column("exam_monitoring_events", sa.Column("risk_score", sa.Integer(), server_default="0", nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)

    if _table_exists("login_rate_limit"):
        op.drop_index("idx_login_rate_limit_key_time", table_name="login_rate_limit")
        op.drop_table("login_rate_limit")

    # Retrait des colonnes ajoutées (ordre inverse)
    for table, cols in [
        ("exam_monitoring_events", ["risk_score"]),
        ("payments", ["receipt_number", "official_import"]),
        ("center_incidents", ["new_attempt_id"]),
        ("exam_question_traces", ["selection_mode", "version_label"]),
        ("device_sessions", ["risk_reason", "last_seen_at"]),
        ("exam_attempts", ["passed", "score"]),
    ]:
        if _table_exists(table):
            existing = {col["name"] for col in insp.get_columns(table)}
            for col in cols:
                if col in existing:
                    op.drop_column(table, col)
