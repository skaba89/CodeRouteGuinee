"""Add auditable refund requests instead of marking manual refunds completed early.

Revision ID: 0017
Revises: 0016
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0017"
down_revision = "0016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "payment_refund_requests",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("payment_id", sa.String(length=36), sa.ForeignKey("payments.id"), nullable=False),
        sa.Column("booking_reference", sa.String(length=80), nullable=False),
        sa.Column("amount_gnf", sa.Integer(), nullable=False),
        sa.Column("provider", sa.String(length=80), nullable=False),
        sa.Column("requested_by_id", sa.String(length=36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False, server_default="requested"),
        sa.Column("decision_reason", sa.Text(), nullable=True),
        sa.Column("decided_by_id", sa.String(length=36), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("provider_refund_reference", sa.String(length=200), nullable=True),
        sa.Column("evidence_reference", sa.String(length=255), nullable=True),
        sa.Column("completion_notes", sa.Text(), nullable=True),
        sa.Column("requested_at", sa.DateTime(), nullable=False),
        sa.Column("decided_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_payment_refund_requests_payment_id", "payment_refund_requests", ["payment_id"])
    op.create_index("ix_payment_refund_requests_booking_reference", "payment_refund_requests", ["booking_reference"])
    op.create_index("ix_payment_refund_requests_status", "payment_refund_requests", ["status"])
    op.create_index("ix_payment_refund_requests_requested_at", "payment_refund_requests", ["requested_at"])


def downgrade() -> None:
    op.drop_index("ix_payment_refund_requests_requested_at", table_name="payment_refund_requests")
    op.drop_index("ix_payment_refund_requests_status", table_name="payment_refund_requests")
    op.drop_index("ix_payment_refund_requests_booking_reference", table_name="payment_refund_requests")
    op.drop_index("ix_payment_refund_requests_payment_id", table_name="payment_refund_requests")
    op.drop_table("payment_refund_requests")
