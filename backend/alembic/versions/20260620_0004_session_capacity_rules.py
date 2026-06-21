"""Session capacity rules: max 35 candidates, 3 sessions/week, commune constraint.

Revision ID: 20260620_0004
Revises: 20260619_0003
Create Date: 2026-06-20
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy import text

revision = "20260620_0004"
down_revision = "20260619_0003"
branch_labels = None
depends_on = None


def _is_pg() -> bool:
    return op.get_bind().dialect.name == "postgresql"


def _is_sqlite() -> bool:
    return op.get_bind().dialect.name == "sqlite"


def _add_column_if_missing(table: str, column: str, col_def: sa.Column) -> None:
    """Ajoute une colonne uniquement si elle n'existe pas déjà."""
    if _is_pg():
        op.get_bind().execute(text(f"""
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_name = '{table}' AND column_name = '{column}'
                ) THEN
                    ALTER TABLE {table} ADD COLUMN {column} {col_def.type.compile(op.get_bind().dialect)};
                END IF;
            END
            $$;
        """))
    elif _is_sqlite():
        # SQLite : pas de IF NOT EXISTS sur ADD COLUMN → on vérifie manuellement
        result = op.get_bind().execute(text(f"PRAGMA table_info({table})"))
        cols = {row[1] for row in result}
        if column not in cols:
            op.add_column(table, col_def)


def _add_check_constraint_if_missing(constraint_name: str, table: str, condition: str) -> None:
    """Crée une contrainte CHECK uniquement si elle n'existe pas — PostgreSQL uniquement."""
    if not _is_pg():
        return
    op.get_bind().execute(text(f"""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conname = '{constraint_name}'
                  AND conrelid = '{table}'::regclass
            ) THEN
                ALTER TABLE {table} ADD CONSTRAINT {constraint_name} CHECK ({condition});
            END IF;
        END
        $$;
    """))


def upgrade() -> None:
    # ── Colonnes Centre ─────────────────────────────────────────────────────
    _add_column_if_missing("centers", "commune",
        sa.Column("commune", sa.String(120), nullable=True))

    _add_column_if_missing("centers", "prefecture",
        sa.Column("prefecture", sa.String(120), nullable=True))

    _add_column_if_missing("centers", "max_sessions_per_week",
        sa.Column("max_sessions_per_week", sa.Integer(), nullable=True))

    _add_column_if_missing("centers", "latitude",
        sa.Column("latitude", sa.Float(), nullable=True))

    _add_column_if_missing("centers", "longitude",
        sa.Column("longitude", sa.Float(), nullable=True))

    # Valeurs par défaut
    op.get_bind().execute(text(
        "UPDATE centers SET max_sessions_per_week = 3 WHERE max_sessions_per_week IS NULL"
    ))

    # Rendre NOT NULL après avoir rempli les valeurs
    if _is_pg():
        op.get_bind().execute(text(
            "ALTER TABLE centers ALTER COLUMN max_sessions_per_week SET NOT NULL"
        ))
        op.get_bind().execute(text(
            "ALTER TABLE centers ALTER COLUMN max_sessions_per_week SET DEFAULT 3"
        ))

    # ── Contraintes CHECK idempotentes (DO $$ IF NOT EXISTS $$) ────────────
    _add_check_constraint_if_missing(
        "ck_centers_max_sessions_per_week",
        "centers",
        "max_sessions_per_week >= 1 AND max_sessions_per_week <= 7",
    )

    # Capacité sessions : cap à 35
    op.get_bind().execute(text(
        "UPDATE exam_sessions SET capacity = 35 WHERE capacity > 35"
    ))

    _add_check_constraint_if_missing(
        "ck_exam_sessions_capacity_max_35",
        "exam_sessions",
        "capacity >= 1 AND capacity <= 35",
    )


def downgrade() -> None:
    if _is_pg():
        # Supprimer les contraintes si elles existent
        op.get_bind().execute(text("""
            DO $$
            BEGIN
                IF EXISTS (
                    SELECT 1 FROM pg_constraint
                    WHERE conname = 'ck_exam_sessions_capacity_max_35'
                      AND conrelid = 'exam_sessions'::regclass
                ) THEN
                    ALTER TABLE exam_sessions DROP CONSTRAINT ck_exam_sessions_capacity_max_35;
                END IF;
                IF EXISTS (
                    SELECT 1 FROM pg_constraint
                    WHERE conname = 'ck_centers_max_sessions_per_week'
                      AND conrelid = 'centers'::regclass
                ) THEN
                    ALTER TABLE centers DROP CONSTRAINT ck_centers_max_sessions_per_week;
                END IF;
            END
            $$;
        """))

    for col in ["longitude", "latitude", "max_sessions_per_week", "prefecture", "commune"]:
        if _is_pg():
            op.get_bind().execute(text(f"""
                DO $$
                BEGIN
                    IF EXISTS (
                        SELECT 1 FROM information_schema.columns
                        WHERE table_name = 'centers' AND column_name = '{col}'
                    ) THEN
                        ALTER TABLE centers DROP COLUMN {col};
                    END IF;
                END
                $$;
            """))
        elif _is_sqlite():
            try:
                op.drop_column("centers", col)
            except Exception:
                pass
