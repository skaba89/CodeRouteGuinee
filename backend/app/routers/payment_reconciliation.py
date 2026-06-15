from collections import Counter
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.deps import require_roles
from app.models_audit import AuditLog
from app.models_payment import Payment
from app.models_user import User

router = APIRouter(prefix="/payments/admin/reconciliation", tags=["payments"])


def _payment_to_row(payment: Payment) -> dict:
    return {
        "reference": payment.reference,
        "booking_reference": payment.booking_reference,
        "amount_gnf": payment.amount_gnf,
        "provider": payment.provider,
        "status": payment.status,
        "receipt_number": payment.receipt_number,
        "created_at": payment.created_at.isoformat() if payment.created_at else None,
    }


def _build_payment_alert(payment: Payment, alert_type: str, severity: str, message: str) -> dict:
    return {
        "type": alert_type,
        "severity": severity,
        "message": message,
        "reference": payment.reference,
        "booking_reference": payment.booking_reference,
        "amount_gnf": payment.amount_gnf,
        "provider": payment.provider,
        "status": payment.status,
        "receipt_number": payment.receipt_number,
        "created_at": payment.created_at.isoformat() if payment.created_at else None,
    }


@router.get("/items")
def list_reconciliation_items(
    provider: str | None = None,
    payment_status: str | None = Query(default=None, alias="status"),
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "super_admin")),
) -> list[dict]:
    safe_limit = max(1, min(limit, 200))
    query = select(Payment)
    if provider:
        query = query.where(Payment.provider == provider)
    if payment_status:
        query = query.where(Payment.status == payment_status)
    if date_from:
        query = query.where(Payment.created_at >= date_from)
    if date_to:
        query = query.where(Payment.created_at <= date_to)
    payments = db.scalars(query.order_by(Payment.created_at.desc()).limit(safe_limit)).all()
    db.add(
        AuditLog(
            actor_id=current_user.id,
            action="payments.reconciliation_items_viewed",
            entity="payment",
            entity_id="national-payments",
            details={
                "payments_returned": len(payments),
                "provider": provider,
                "status": payment_status,
                "date_from": date_from.isoformat() if date_from else None,
                "date_to": date_to.isoformat() if date_to else None,
                "limit": safe_limit,
            },
        )
    )
    db.commit()
    return [_payment_to_row(payment) for payment in payments]


@router.get("/alerts")
def list_reconciliation_alerts(
    provider: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "super_admin")),
) -> list[dict]:
    safe_limit = max(1, min(limit, 300))
    query = select(Payment)
    if provider:
        query = query.where(Payment.provider == provider)
    if date_from:
        query = query.where(Payment.created_at >= date_from)
    if date_to:
        query = query.where(Payment.created_at <= date_to)
    payments = list(db.scalars(query.order_by(Payment.created_at.desc()).limit(safe_limit)).all())

    booking_counts = Counter(payment.booking_reference for payment in payments if payment.booking_reference)
    receipt_counts = Counter(payment.receipt_number for payment in payments if payment.receipt_number)
    alerts: list[dict] = []

    for payment in payments:
        if payment.status in {"failed", "pending"}:
            severity = "high" if payment.status == "failed" else "medium"
            alerts.append(_build_payment_alert(payment, "status", severity, f"Paiement {payment.status} a verifier"))
        if payment.amount_gnf <= 0 or payment.amount_gnf > 1_000_000:
            alerts.append(_build_payment_alert(payment, "amount", "high", "Montant inhabituel pour un paiement d'examen"))
        if booking_counts[payment.booking_reference] > 1:
            alerts.append(_build_payment_alert(payment, "duplicate_booking", "medium", "Plusieurs paiements pour la meme reservation"))
        if receipt_counts[payment.receipt_number] > 1:
            alerts.append(_build_payment_alert(payment, "duplicate_receipt", "high", "Numero de recu duplique"))

    db.add(
        AuditLog(
            actor_id=current_user.id,
            action="payments.alerts_viewed",
            entity="payment",
            entity_id="national-payments",
            details={
                "alerts_returned": len(alerts),
                "payments_scanned": len(payments),
                "provider": provider,
                "date_from": date_from.isoformat() if date_from else None,
                "date_to": date_to.isoformat() if date_to else None,
                "limit": safe_limit,
            },
        )
    )
    db.commit()
    return alerts[:safe_limit]
