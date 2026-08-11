"""Compatibility facade for legacy registration booking endpoints.

The frontend now uses /bookings/self, but older clients may still call
/registration/availability and /registration/book. These routes must obey the
same transactional rules rather than carrying a second, weaker implementation.
"""
from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.booking_rules import (
    acquire_booking_reference_lock,
    assert_no_active_booking,
    assert_session_has_capacity,
    lock_bookable_session,
)
from app.booking_service import build_booking_reference, build_verification_code
from app.db.session import get_db
from app.deps import get_current_user, require_roles
from app.models_audit import AuditLog
from app.models_booking import Booking
from app.models_candidate import Candidate
from app.models_center import Center
from app.models_session import ExamSession
from app.models_user import User

router = APIRouter(prefix="/registration", tags=["registration"])


class BookSessionIn(BaseModel):
    session_id: str = Field(min_length=8, max_length=64)


def _my_candidate(db: Session, current_user: User) -> Candidate:
    candidate = db.scalar(select(Candidate).where(Candidate.user_id == current_user.id))
    if not candidate and current_user.email:
        candidate = db.scalar(select(Candidate).where(Candidate.email == current_user.email))
    if not candidate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Aucune fiche candidat liée à ce compte. Complétez votre inscription.",
        )
    return candidate


@router.get("/availability")
def get_legacy_availability(
    prefecture: str | None = Query(default=None),
    center_id: str | None = Query(default=None),
    limit: int = Query(default=60, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Compatibility shape backed by the canonical availability invariants."""
    now = datetime.now(UTC).replace(tzinfo=None)
    query = (
        select(ExamSession, Center)
        .join(Center, ExamSession.center_id == Center.id)
        .where(
            ExamSession.starts_at > now,
            ExamSession.status.in_(["planned", "open"]),
            Center.status.in_(["active", "accredited"]),
        )
        .order_by(ExamSession.starts_at.asc())
        .limit(limit * 2)
    )
    if center_id:
        query = query.where(ExamSession.center_id == center_id)
    if prefecture:
        query = query.where(Center.prefecture == prefecture)

    rows = db.execute(query).all()
    session_ids = [session.id for session, _ in rows]
    booked: dict[str, int] = {}
    if session_ids:
        booked = dict(
            db.execute(
                select(Booking.session_id, func.count(Booking.id))
                .where(
                    Booking.session_id.in_(session_ids),
                    Booking.status.not_in(["cancelled"]),
                )
                .group_by(Booking.session_id)
            ).all()
        )

    items: list[dict] = []
    for session, center in rows:
        seats_left = max(0, session.capacity - booked.get(session.id, 0))
        if seats_left <= 0:
            continue
        items.append(
            {
                "session_id": session.id,
                "session_reference": session.reference,
                "starts_at": session.starts_at.isoformat(),
                "capacity": session.capacity,
                "seats_left": seats_left,
                "center_id": center.id,
                "center_name": center.name,
                "center_city": center.city,
                "center_prefecture": center.prefecture,
                "center_commune": center.commune,
            }
        )
        if len(items) >= limit:
            break

    return {
        "items": items,
        "total": len(items),
        "prefectures": sorted({item["center_prefecture"] for item in items if item["center_prefecture"]}),
    }


@router.post("/book", status_code=status.HTTP_201_CREATED)
def book_legacy_session(
    payload: BookSessionIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("candidate")),
) -> dict:
    candidate = _my_candidate(db, current_user)
    session, center = lock_bookable_session(db, payload.session_id)
    assert_no_active_booking(db, candidate.id)
    assert_session_has_capacity(db, session)

    acquire_booking_reference_lock(db)
    sequence = (db.scalar(select(func.count(Booking.id))) or 0) + 1
    reference = build_booking_reference(sequence)
    booking = Booking(
        reference=reference,
        candidate_id=candidate.id,
        session_id=session.id,
        status="confirmed",
        verification_code=build_verification_code(reference),
        notes="Réservation legacy sécurisée — règles canoniques /bookings/self",
    )
    db.add(booking)
    db.flush()
    db.add(
        AuditLog(
            actor_id=current_user.id,
            action="registration.self_booking_legacy",
            entity="booking",
            entity_id=booking.id,
            details={
                "reference": booking.reference,
                "session_id": session.id,
                "center_id": center.id,
                "compatibility_route": "/registration/book",
            },
        )
    )
    db.commit()
    db.refresh(booking)

    return {
        "booking_reference": booking.reference,
        "verification_code": booking.verification_code,
        "status": booking.status,
        "session_reference": session.reference,
        "starts_at": session.starts_at.isoformat(),
        "center_name": center.name,
        "center_city": center.city,
    }
