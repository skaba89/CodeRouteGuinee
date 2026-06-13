from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.entry_service import build_entry_denied, build_entry_success
from app.models_audit import AuditLog
from app.models_booking import Booking

router = APIRouter(prefix="/entries", tags=["entries"])


class EntryIn(BaseModel):
    reference: str
    verification_code: str
    center_code: str | None = None


def _record_entry_log(db: Session, reference: str, result: str, reason: str | None, center_code: str | None) -> None:
    db.add(
        AuditLog(
            action="entry_validation",
            entity="booking",
            details={
                "reference": reference,
                "result": result,
                "reason": reason,
                "center_code": center_code,
            },
        )
    )


@router.post("/validate")
def validate_entry(payload: EntryIn, db: Session = Depends(get_db)) -> dict:
    booking = db.scalar(select(Booking).where(Booking.reference == payload.reference))
    if not booking:
        _record_entry_log(db, payload.reference, "denied", "booking_not_found", payload.center_code)
        db.commit()
        return build_entry_denied(payload.reference, "booking_not_found")
    if booking.verification_code != payload.verification_code:
        _record_entry_log(db, payload.reference, "denied", "invalid_verification_code", payload.center_code)
        db.commit()
        return build_entry_denied(payload.reference, "invalid_verification_code")
    if booking.status == "checked_in":
        _record_entry_log(db, payload.reference, "denied", "already_checked_in", payload.center_code)
        db.commit()
        return build_entry_denied(payload.reference, "already_checked_in")
    booking.status = "checked_in"
    db.add(booking)
    _record_entry_log(db, payload.reference, "allowed", None, payload.center_code)
    db.commit()
    return build_entry_success(payload.reference, payload.center_code)
