"""
Migration 0009 — seed admin super_admin

Insère l'utilisateur super_admin@coderoute.gov.gn directement en base.
Idempotent : ne fait rien si l'utilisateur existe déjà.

Revision ID: 0009
Revises: 0008
Create Date: 2026-07-01
"""
from __future__ import annotations
from alembic import op
from sqlalchemy import text

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Migration 0009 : le compte super_admin est créé par entrypoint.sh
    via BOOTSTRAP_ADMIN_EMAIL / BOOTSTRAP_ADMIN_PASSWORD (Render Dashboard).
    Cette migration vérifie uniquement que la table users est accessible.
    """
    bind = op.get_bind()
    # Vérification de sanité : la table users doit exister
    bind.execute(text("SELECT 1 FROM users LIMIT 1"))


def downgrade() -> None:
    op.get_bind().execute(
        text("DELETE FROM users WHERE email = 'super_admin@coderoute.gov.gn'")
    )
