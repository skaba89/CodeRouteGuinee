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
    bind = op.get_bind()

    # Idempotent : ne rien faire si l'admin existe déjà
    existing = bind.execute(
        text("SELECT id FROM users WHERE email = 'super_admin@coderoute.gov.gn'")
    ).fetchone()

    if existing:
        return  # déjà présent

    bind.execute(text("""
        INSERT INTO users (
            id, email, full_name, password_hash,
            role, is_active, center_id, created_at
        ) VALUES (
            'b6db6bac-53bf-4ad5-a8d1-48cdccc6445c',
            'super_admin@coderoute.gov.gn',
            'Directeur National CodeRoute',
            '$2b$12$YYxswN/DntsFQhU22sX57OW1WWr8x5Qq4wZT7A84qEDWQbYIXjhiS',
            'super_admin',
            true,
            NULL,
            NOW()
        )
    """))


def downgrade() -> None:
    op.get_bind().execute(
        text("DELETE FROM users WHERE email = 'super_admin@coderoute.gov.gn'")
    )
