from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.deps import get_current_user
from app.models_booking import Booking
from app.models_candidate import Candidate
from app.models_user import User
from app.payment_rules import assert_payment_booking_access, resolve_authoritative_amount

router = APIRouter()


@router.get("/quote/{booking_reference}")
def get_payment_quote(
    booking_reference: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Retourne le prix serveur applicable à une réservation accessible."""
    booking = db.scalar(select(Booking).where(Booking.reference == booking_reference.strip()))
    if not booking:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found")
    assert_payment_booking_access(db, current_user, booking)
    if booking.status == "cancelled":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Cette réservation est annulée.")

    candidate = db.get(Candidate, booking.candidate_id)
    amount = resolve_authoritative_amount(db, booking)
    return {
        "booking_reference": booking.reference,
        "amount_gnf": amount,
        "currency": "GNF",
        "permit_category": candidate.permit_category if candidate else None,
        "attempt_number": (candidate.attempt_count or 0) + 1 if candidate else None,
        "source": "server_tariff",
    }
