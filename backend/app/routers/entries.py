from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.deps import require_roles
from app.entry_service import build_entry_denied, build_entry_success
from app.models_audit import AuditLog
from app.models_booking import Booking
from app.models_user import User

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
def validate_entry(
    payload: EntryIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("center", "admin", "super_admin")),
) -> dict:
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


@router.get("/summary")
def get_entry_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "super_admin")),
) -> dict:
    logs = db.scalars(select(AuditLog).where(AuditLog.action == "entry_validation")).all()
    total = 0
    by_result: dict[str, int] = {}
    by_center: dict[str, dict[str, int]] = {}
    for log in logs:
        details = log.details or {}
        result = details.get("result", "unknown")
        center_code = details.get("center_code") or "unknown"
        total += 1
        by_result[result] = by_result.get(result, 0) + 1
        by_center.setdefault(center_code, {"allowed": 0, "denied": 0})
        if result in by_center[center_code]:
            by_center[center_code][result] += 1
    return {"total": total, "by_result": by_result, "by_center": by_center}


@router.get("/logs")
def list_entry_logs(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "super_admin")),
) -> list[dict]:
    logs = db.scalars(select(AuditLog).where(AuditLog.action == "entry_validation").order_by(AuditLog.created_at.desc()).limit(100)).all()
    return [
        {
            "id": log.id,
            "details": log.details,
            "created_at": log.created_at.isoformat(),
        }
        for log in logs
    ]
