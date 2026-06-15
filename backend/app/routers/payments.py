from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.deps import require_roles
from app.mobile_money import simulate_mobile_money_payment
from app.models_audit import AuditLog
from app.models_booking import Booking
from app.models_payment import Payment
from app.models_user import User
from app.payment_recap import summarize_payments
from app.payment_service import build_payment_reference, build_receipt_number

router = APIRouter(prefix="/payments", tags=["payments"])


class PaymentIn(BaseModel):
    booking_reference: str
    amount_gnf: int = 250000
    provider: str = "sandbox"
    phone: str


@router.post("", status_code=status.HTTP_201_CREATED)
def create_payment(payload: PaymentIn, db: Session = Depends(get_db)) -> dict:
    booking = db.scalar(select(Booking).where(Booking.reference == payload.booking_reference))
    if not booking:
        db.add(
            AuditLog(
                actor_id=None,
                action="payment.failed",
                entity="payment",
                entity_id=payload.booking_reference,
                details={
                    "reason": "booking_not_found",
                    "booking_reference": payload.booking_reference,
                    "amount_gnf": payload.amount_gnf,
                    "provider": payload.provider,
                },
            )
        )
        db.commit()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found")
    provider_result = simulate_mobile_money_payment(payload.provider, payload.phone, payload.amount_gnf)
    reference = build_payment_reference(db.query(Payment).count() + 1)
    payment = Payment(
        reference=reference,
        booking_reference=payload.booking_reference,
        amount_gnf=payload.amount_gnf,
        provider=provider_result.provider,
        phone=payload.phone,
        status=provider_result.status,
        receipt_number=build_receipt_number(reference),
    )
    db.add(payment)
    db.add(
        AuditLog(
            actor_id=None,
            action="payment.created",
            entity="payment",
            entity_id=reference,
            details={
                "booking_reference": payload.booking_reference,
                "amount_gnf": payload.amount_gnf,
                "provider": provider_result.provider,
                "status": provider_result.status,
                "receipt_number": payment.receipt_number,
                "external_reference": provider_result.external_reference,
            },
        )
    )
    db.commit()
    db.refresh(payment)
    return {
        "reference": payment.reference,
        "booking_reference": payment.booking_reference,
        "amount_gnf": payment.amount_gnf,
        "provider": payment.provider,
        "status": payment.status,
        "receipt_number": payment.receipt_number,
        "external_reference": provider_result.external_reference,
        "message": provider_result.message,
    }


@router.get("/recap/summary")
def get_payment_summary(db: Session = Depends(get_db)) -> dict:
    payments = db.scalars(select(Payment)).all()
    return summarize_payments(payments)


@router.get("/admin/summary")
def get_admin_payment_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "super_admin")),
) -> dict:
    payments = db.scalars(select(Payment)).all()
    summary = summarize_payments(payments)
    db.add(
        AuditLog(
            actor_id=current_user.id,
            action="payments.summary_viewed",
            entity="payment",
            entity_id="national-payments",
            details={
                "total_count": summary["total_count"],
                "total_amount_gnf": summary["total_amount_gnf"],
            },
        )
    )
    db.commit()
    return summary


@router.get("/{reference}")
def get_payment(reference: str, db: Session = Depends(get_db)) -> dict:
    payment = db.scalar(select(Payment).where(Payment.reference == reference))
    if not payment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found")
    return {
        "reference": payment.reference,
        "booking_reference": payment.booking_reference,
        "amount_gnf": payment.amount_gnf,
        "provider": payment.provider,
        "status": payment.status,
        "receipt_number": payment.receipt_number,
    }
