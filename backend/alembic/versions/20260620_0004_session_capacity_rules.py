"""Session capacity rules: max 35 candidates, 3 sessions/week, commune constraint.

Revision ID: 20260620_0004
Revises: 20260619_0003
Create Date: 2026-06-20
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine import reflection

revision = "20260620_0004"
down_revision = "20260619_0003"
branch_labels = None
depends_on = None


def _is_sqlite() -> bool:
    return op.get_bind().dialect.name == "sqlite"


def upgrade() -> None:
    bind = op.get_bind()
    inspector = reflection.Inspector.from_engine(bind)

    # ── Colonnes Centre ────────────────────────────────────────────
    center_cols = {c["name"] for c in inspector.get_columns("centers")}

    if "commune" not in center_cols:
        op.add_column("centers", sa.Column("commune", sa.String(120), nullable=True))

    if "prefecture" not in center_cols:
        op.add_column("centers", sa.Column("prefecture", sa.String(120), nullable=True))

    if "max_sessions_per_week" not in center_cols:
        op.add_column(
            "centers",
            sa.Column("max_sessions_per_week", sa.Integer(), nullable=False, server_default="3"),
        )

    if "latitude" not in center_cols:
        op.add_column("centers", sa.Column("latitude", sa.Float(), nullable=True))

    if "longitude" not in center_cols:
        op.add_column("centers", sa.Column("longitude", sa.Float(), nullable=True))

    # Valeurs par défaut pour les centres existants
    op.execute("UPDATE centers SET max_sessions_per_week = 3 WHERE max_sessions_per_week IS NULL")

    # CHECK constraint uniquement sur PostgreSQL (SQLite les ignore)
    if not _is_sqlite():
        try:
            op.create_check_constraint(
                "ck_centers_max_sessions_per_week",
                "centers",
                "max_sessions_per_week >= 1 AND max_sessions_per_week <= 7",
            )
        except Exception:
            pass  # Contrainte déjà existante

    # ── Capacité sessions ──────────────────────────────────────────
    # Correction : capacity max = 35 (règle DNTT)
    op.execute("UPDATE exam_sessions SET capacity = 35 WHERE capacity > 35")

    if not _is_sqlite():
        try:
            op.create_check_constraint(
                "ck_exam_sessions_capacity_max_35",
                "exam_sessions",
                "capacity >= 1 AND capacity <= 35",
            )
        except Exception:
            pass


def downgrade() -> None:
    bind = op.get_bind()
    if not bind.dialect.name == "sqlite":
        try:
            op.drop_constraint("ck_exam_sessions_capacity_max_35", "exam_sessions", type_="check")
        except Exception:
            pass
        try:
            op.drop_constraint("ck_centers_max_sessions_per_week", "centers", type_="check")
        except Exception:
            pass

    for col in ["longitude", "latitude", "max_sessions_per_week", "prefecture", "commune"]:
        try:
            op.drop_column("centers", col)
        except Exception:
            pass
