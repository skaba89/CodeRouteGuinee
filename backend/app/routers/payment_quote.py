from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.deps import get_current_user
from app.models_booking import Booking
from app.models_candidate import Candidate
from app.models_payment import Payment
from app.models_user import User
from app.payment_rules import (
    assert_booking_can_start_payment,
    assert_payment_booking_access,
    resolve_authoritative_amount,
)

router = APIRouter()


@router.get("/quote/{booking_reference}")
def get_payment_quote(
    booking_reference: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Retourne le prix serveur ou le paiement idempotent déjà ouvert."""
    booking = db.scalar(select(Booking).where(Booking.reference == booking_reference.strip()))
    if not booking:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found")
    assert_payment_booking_access(db, current_user, booking)

    candidate = db.get(Candidate, booking.candidate_id)
    existing = db.scalar(
        select(Payment)
        .where(
            Payment.booking_reference == booking.reference,
            Payment.status.in_(["paid", "pending"]),
        )
        .order_by(Payment.created_at.desc())
        .limit(1)
    )
    if existing is not None:
        return {
            "booking_reference": booking.reference,
            "amount_gnf": existing.amount_gnf,
            "currency": "GNF",
            "permit_category": candidate.permit_category if candidate else None,
            "attempt_number": (candidate.attempt_count or 0) + 1 if candidate else None,
            "source": "existing_payment",
            "payment_reference": existing.reference,
            "payment_status": existing.status,
            "checkout_url": existing.checkout_url,
        }

    assert_booking_can_start_payment(db, booking)
    amount = resolve_authoritative_amount(db, booking)
    return {
        "booking_reference": booking.reference,
        "amount_gnf": amount,
        "currency": "GNF",
        "permit_category": candidate.permit_category if candidate else None,
        "attempt_number": (candidate.attempt_count or 0) + 1 if candidate else None,
        "source": "server_tariff",
        "payment_reference": None,
        "payment_status": None,
        "checkout_url": None,
    }
