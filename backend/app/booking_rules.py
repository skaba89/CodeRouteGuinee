from __future__ import annotations

from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.models_booking import Booking
from app.models_center import Center
from app.models_session import ExamSession

_BOOKING_REFERENCE_LOCK_ID = 2026081102
_OPERATIONAL_CENTER_STATUSES = {"active", "accredited"}


def acquire_booking_reference_lock(db: Session) -> None:
    if db.get_bind().dialect.name == "postgresql":
        db.execute(text("SELECT pg_advisory_xact_lock(:lock_id)"), {"lock_id": _BOOKING_REFERENCE_LOCK_ID})


def lock_bookable_session(db: Session, session_id: str) -> tuple[ExamSession, Center]:
    session = db.scalar(select(ExamSession).where(ExamSession.id == session_id).with_for_update())
    if not session or session.status not in {"planned", "open"}:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session introuvable ou fermée.")
    now = datetime.now(UTC).replace(tzinfo=None)
    if session.starts_at <= now:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Cette session est déjà passée.")
    center = db.get(Center, session.center_id)
    if not center or center.status not in _OPERATIONAL_CENTER_STATUSES:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Le centre de cette session n'est pas opérationnel.")
    return session, center


def assert_no_active_booking(db: Session, candidate_id: str) -> None:
    now = datetime.now(UTC).replace(tzinfo=None)
    active = db.scalar(
        select(Booking)
        .join(ExamSession, Booking.session_id == ExamSession.id)
        .where(
            Booking.candidate_id == candidate_id,
            Booking.status.not_in(["cancelled"]),
            ExamSession.status.not_in(["cancelled", "archived"]),
            ExamSession.starts_at > now,
        )
        .limit(1)
    )
    if active:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Une réservation active existe déjà : {active.reference}.",
        )


def assert_session_has_capacity(db: Session, session: ExamSession) -> int:
    booked = db.scalar(
        select(func.count(Booking.id)).where(
            Booking.session_id == session.id,
            Booking.status.not_in(["cancelled"]),
        )
    ) or 0
    if booked >= session.capacity:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Cette session est complète. Choisissez un autre créneau.")
    return max(0, session.capacity - booked)
