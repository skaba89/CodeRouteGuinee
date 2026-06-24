"""
Migration 0006 — Tables manquantes et champs absents

Corrige les problèmes critiques identifiés en audit :
  1. Table tfa_secrets (authentification 2FA TOTP)
  2. Table tarifs (tarifs dynamiques configurables)
  3. Tables e-learning : courses, lessons, lesson_progress
  4. Champs manquants sur bookings : notes, cancelled_at
  5. Champs manquants sur candidates : city, date_of_birth, address, attempt_count

Revision ID: 0006
Revises: 0005
Create Date: 2026-06-24
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision      = "0006"
down_revision = "20260623_0005"
branch_labels = None
depends_on    = None


def _col_exists(connection, table: str, col: str) -> bool:
    """Vérifie si une colonne existe dans la table (SQLite + PostgreSQL)."""
    try:
        result = connection.execute(
            sa.text("SELECT column_name FROM information_schema.columns "
                    "WHERE table_name=:t AND column_name=:c"),
            {"t": table, "c": col},
        ).fetchone()
        return result is not None
    except Exception:
        # SQLite fallback
        try:
            rows = connection.execute(sa.text(f"PRAGMA table_info({table})")).fetchall()  # noqa: S608
            return any(r[1] == col for r in rows)
        except Exception:
            return False


def _table_exists(connection, table: str) -> bool:
    try:
        result = connection.execute(
            sa.text("SELECT table_name FROM information_schema.tables WHERE table_name=:t"),
            {"t": table},
        ).fetchone()
        return result is not None
    except Exception:
        try:
            result = connection.execute(
                sa.text("SELECT name FROM sqlite_master WHERE type='table' AND name=:t"),
                {"t": table},
            ).fetchone()
            return result is not None
        except Exception:
            return False


def upgrade() -> None:
    bind = op.get_bind()

    # ── 1. tfa_secrets (2FA TOTP) ─────────────────────────────────────────────
    if not _table_exists(bind, "tfa_secrets"):
        op.create_table(
            "tfa_secrets",
            sa.Column("id",           sa.String(36),  primary_key=True),
            sa.Column("user_id",      sa.String(36),  nullable=False, unique=True),
            sa.Column("secret_b32",   sa.String(200), nullable=False),
            sa.Column("backup_codes", sa.Text(),       nullable=False, server_default="[]"),
            sa.Column("enabled",      sa.Boolean(),   nullable=False, server_default="false"),
            sa.Column("created_at",   sa.DateTime(),  server_default=sa.func.now()),
            sa.Column("updated_at",   sa.DateTime(),  server_default=sa.func.now()),
        )
        op.create_index("ix_tfa_secrets_user_id", "tfa_secrets", ["user_id"])

    # ── 2. tarifs ─────────────────────────────────────────────────────────────
    if not _table_exists(bind, "tarifs"):
        op.create_table(
            "tarifs",
            sa.Column("cle",              sa.String(80),  primary_key=True),
            sa.Column("libelle",          sa.String(200), nullable=False),
            sa.Column("montant_gnf",      sa.Integer(),   nullable=False),
            sa.Column("categorie_permis", sa.String(10),  nullable=True),
            sa.Column("description",      sa.Text(),      nullable=True),
            sa.Column("actif",            sa.Boolean(),   nullable=False, server_default="true"),
            sa.Column("created_at",       sa.DateTime(),  server_default=sa.func.now()),
            sa.Column("updated_at",       sa.DateTime(),  server_default=sa.func.now()),
        )
        # Seed des tarifs par défaut
        bind.execute(sa.text("""
            INSERT INTO tarifs (cle, libelle, montant_gnf, categorie_permis, description)
            VALUES
              ('examen_code_B', 'Examen code route — Permis B', 150000, 'B', 'Frais examen théorique permis B'),
              ('examen_code_A', 'Examen code route — Permis A', 100000, 'A', 'Frais examen théorique permis A'),
              ('examen_code_C', 'Examen code route — Permis C', 200000, 'C', 'Frais examen théorique permis C'),
              ('examen_code_D', 'Examen code route — Permis D', 200000, 'D', 'Frais examen théorique permis D'),
              ('frais_reinscription', 'Frais réinscription 2e tentative', 50000, NULL, 'Frais à partir de la 2e tentative'),
              ('frais_rattrapage',    'Frais rattrapage 3e tentative+',   30000, NULL, 'Tarif réduit 3e tentative et plus')
        """))

    # ── 3. E-learning ─────────────────────────────────────────────────────────
    if not _table_exists(bind, "courses"):
        op.create_table(
            "courses",
            sa.Column("id",          sa.String(36),  primary_key=True),
            sa.Column("title",       sa.String(200), nullable=False),
            sa.Column("description", sa.Text(),      nullable=True),
            sa.Column("category",    sa.String(80),  nullable=True),
            sa.Column("order",       sa.Integer(),   nullable=False, server_default="0"),
            sa.Column("is_active",   sa.Boolean(),   nullable=False, server_default="true"),
            sa.Column("cover_url",   sa.Text(),      nullable=True),
            sa.Column("created_at",  sa.DateTime(),  server_default=sa.func.now()),
            sa.Column("updated_at",  sa.DateTime(),  server_default=sa.func.now()),
        )

    if not _table_exists(bind, "lessons"):
        op.create_table(
            "lessons",
            sa.Column("id",                     sa.String(36),  primary_key=True),
            sa.Column("course_id",              sa.String(36),  nullable=False),
            sa.Column("title",                  sa.String(200), nullable=False),
            sa.Column("content",                sa.Text(),      nullable=False),
            sa.Column("order",                  sa.Integer(),   nullable=False, server_default="0"),
            sa.Column("video_url",              sa.Text(),      nullable=True),
            sa.Column("video_duration_seconds", sa.Integer(),   nullable=True),
            sa.Column("duration_minutes",       sa.Integer(),   nullable=False, server_default="5"),
            sa.Column("is_active",              sa.Boolean(),   nullable=False, server_default="true"),
            sa.Column("slug",                   sa.String(120), nullable=True),
            sa.Column("created_at",             sa.DateTime(),  server_default=sa.func.now()),
            sa.Column("updated_at",             sa.DateTime(),  server_default=sa.func.now()),
            sa.ForeignKeyConstraint(["course_id"], ["courses.id"], ondelete="CASCADE"),
        )
        op.create_index("ix_lessons_course_id", "lessons", ["course_id"])

    if not _table_exists(bind, "lesson_progress"):
        op.create_table(
            "lesson_progress",
            sa.Column("id",           sa.String(36),  primary_key=True),
            sa.Column("candidate_id", sa.String(36),  nullable=False),
            sa.Column("lesson_id",    sa.String(36),  nullable=False),
            sa.Column("completed",    sa.Boolean(),   nullable=False, server_default="false"),
            sa.Column("progress_pct", sa.Integer(),   nullable=False, server_default="0"),
            sa.Column("last_seen_at", sa.DateTime(),  nullable=True),
            sa.Column("completed_at", sa.DateTime(),  nullable=True),
            sa.UniqueConstraint("candidate_id", "lesson_id", name="uq_lesson_progress"),
            sa.ForeignKeyConstraint(["lesson_id"], ["lessons.id"], ondelete="CASCADE"),
        )
        op.create_index("ix_lesson_progress_candidate", "lesson_progress", ["candidate_id"])

    # ── 4. bookings — colonnes manquantes ─────────────────────────────────────
    if not _col_exists(bind, "bookings", "notes"):
        op.add_column("bookings", sa.Column("notes", sa.Text(), nullable=True))

    if not _col_exists(bind, "bookings", "cancelled_at"):
        op.add_column("bookings", sa.Column("cancelled_at", sa.DateTime(), nullable=True))

    if not _col_exists(bind, "bookings", "payment_reference"):
        op.add_column("bookings", sa.Column("payment_reference", sa.String(80), nullable=True))

    # ── 5. candidates — colonnes manquantes ───────────────────────────────────
    if not _col_exists(bind, "candidates", "city"):
        op.add_column("candidates", sa.Column("city", sa.String(100), nullable=True))

    if not _col_exists(bind, "candidates", "date_of_birth"):
        op.add_column("candidates", sa.Column("date_of_birth", sa.Date(), nullable=True))

    if not _col_exists(bind, "candidates", "address"):
        op.add_column("candidates", sa.Column("address", sa.Text(), nullable=True))

    if not _col_exists(bind, "candidates", "attempt_count"):
        op.add_column(
            "candidates",
            sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        )


def downgrade() -> None:
    bind = op.get_bind()

    # Supprimer dans l'ordre inverse (FK d'abord)
    for table in ["lesson_progress", "lessons", "courses", "tarifs", "tfa_secrets"]:
        if _table_exists(bind, table):
            op.drop_table(table)

    # Supprimer les colonnes ajoutées
    for col in ["notes", "cancelled_at", "payment_reference"]:
        if _col_exists(bind, "bookings", col):
            op.drop_column("bookings", col)

    for col in ["city", "date_of_birth", "address", "attempt_count"]:
        if _col_exists(bind, "candidates", col):
            op.drop_column("candidates", col)
