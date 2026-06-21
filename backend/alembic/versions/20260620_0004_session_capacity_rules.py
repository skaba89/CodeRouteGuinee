"""Session capacity rules: max 35 candidates, 3 sessions/week, commune constraint.

Revision ID: 20260620_0004
Revises: 20260619_0003
Create Date: 2026-06-20
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect, text

revision = "20260620_0004"
down_revision = "20260619_0003"
branch_labels = None
depends_on = None


def _dialect() -> str:
    return op.get_bind().dialect.name


def _column_exists(table: str, column: str) -> bool:
    insp = inspect(op.get_bind())
    return column in {c["name"] for c in insp.get_columns(table)}


def _constraint_exists(table: str, constraint_name: str) -> bool:
    """Vérifie l'existence d'une contrainte CHECK via pg_constraint (PostgreSQL uniquement)."""
    if _dialect() == "sqlite":
        return False
    result = op.get_bind().execute(
        text(
            "SELECT 1 FROM pg_constraint "
            "WHERE conname = :name AND conrelid = :table::regclass"
        ),
        {"name": constraint_name, "table": table},
    )
    return result.fetchone() is not None


def upgrade() -> None:
    # ── Colonnes Centre ────────────────────────────────────────────────────
    if not _column_exists("centers", "commune"):
        op.add_column("centers", sa.Column("commune", sa.String(120), nullable=True))

    if not _column_exists("centers", "prefecture"):
        op.add_column("centers", sa.Column("prefecture", sa.String(120), nullable=True))

    if not _column_exists("centers", "max_sessions_per_week"):
        op.add_column(
            "centers",
            sa.Column("max_sessions_per_week", sa.Integer(), nullable=False, server_default="3"),
        )

    if not _column_exists("centers", "latitude"):
        op.add_column("centers", sa.Column("latitude", sa.Float(), nullable=True))

    if not _column_exists("centers", "longitude"):
        op.add_column("centers", sa.Column("longitude", sa.Float(), nullable=True))

    # Valeurs par défaut
    op.execute(text("UPDATE centers SET max_sessions_per_week = 3 WHERE max_sessions_per_week IS NULL"))

    # ── Contraintes CHECK — idempotentes via vérification préalable ────────
    if _dialect() != "sqlite":
        if not _constraint_exists("centers", "ck_centers_max_sessions_per_week"):
            op.create_check_constraint(
                "ck_centers_max_sessions_per_week",
                "centers",
                "max_sessions_per_week >= 1 AND max_sessions_per_week <= 7",
            )

    # ── Capacité sessions ──────────────────────────────────────────────────
    op.execute(text("UPDATE exam_sessions SET capacity = 35 WHERE capacity > 35"))

    if _dialect() != "sqlite":
        if not _constraint_exists("exam_sessions", "ck_exam_sessions_capacity_max_35"):
            op.create_check_constraint(
                "ck_exam_sessions_capacity_max_35",
                "exam_sessions",
                "capacity >= 1 AND capacity <= 35",
            )


def downgrade() -> None:
    if _dialect() != "sqlite":
        if _constraint_exists("exam_sessions", "ck_exam_sessions_capacity_max_35"):
            op.drop_constraint("ck_exam_sessions_capacity_max_35", "exam_sessions", type_="check")
        if _constraint_exists("centers", "ck_centers_max_sessions_per_week"):
            op.drop_constraint("ck_centers_max_sessions_per_week", "centers", type_="check")

    for col in ["longitude", "latitude", "max_sessions_per_week", "prefecture", "commune"]:
        if _column_exists("centers", col):
            op.drop_column("centers", col)
