from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.entry_service import build_entry_denied, build_entry_success
from app.models_booking import Booking

router = APIRouter(prefix="/entries", tags=["entries"])


class EntryIn(BaseModel):
    reference: str
    verification_code: str
    center_code: str | None = None


@router.post("/validate")
def validate_entry(payload: EntryIn, db: Session = Depends(get_db)) -> dict:
    booking = db.scalar(select(Booking).where(Booking.reference == payload.reference))
    if not booking:
        return build_entry_denied(payload.reference, "booking_not_found")
    if booking.verification_code != payload.verification_code:
        return build_entry_denied(payload.reference, "invalid_verification_code")
    if booking.status == "checked_in":
        return build_entry_denied(payload.reference, "already_checked_in")
    booking.status = "checked_in"
    db.add(booking)
    db.commit()
    return build_entry_success(payload.reference, payload.center_code)
