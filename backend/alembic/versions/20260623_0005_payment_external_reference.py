"""payment external_reference + paid_at

Revision ID: 0005
Revises: 0004
Create Date: 2026-06-23
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260623_0005"
down_revision = "20260620_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    from sqlalchemy import inspect, text

    bind = op.get_bind()
    inspector = inspect(bind)

    # Colonne email sur les candidats (notifications)
    cand_cols = [c["name"] for c in inspector.get_columns("candidates")]
    if "email" not in cand_cols:
        op.add_column("candidates", sa.Column("email", sa.String(200), nullable=True))
        # Index uniquement si la colonne vient d'être créée
        try:
            op.create_index("ix_candidates_email", "candidates", ["email"], unique=False)
        except Exception:
            pass

    # Colonnes external_reference et paid_at sur les paiements (webhooks)
    pay_cols = [c["name"] for c in inspector.get_columns("payments")]
    if "external_reference" not in pay_cols:
        op.add_column("payments", sa.Column("external_reference", sa.String(200), nullable=True))
        try:
            op.create_index("ix_payments_external_reference", "payments", ["external_reference"], unique=False)
        except Exception:
            pass

    if "paid_at" not in pay_cols:
        op.add_column("payments", sa.Column("paid_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    op.drop_index("ix_candidates_email", table_name="candidates")
    op.drop_column("candidates", "email")
    # Paiements
    op.drop_index("ix_payments_external_reference", table_name="payments")
    op.drop_column("payments", "paid_at")
    op.drop_column("payments", "external_reference")
