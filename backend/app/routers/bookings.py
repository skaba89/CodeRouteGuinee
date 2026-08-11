from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.booking_rules import (
    acquire_booking_reference_lock,
    assert_no_active_booking,
    assert_session_has_capacity,
    lock_bookable_session,
)
from app.booking_service import build_booking_reference, build_verification_code
from app.convocation_service import build_convocation_payload
from app.db.session import get_db
from app.deps import get_current_user, require_roles
from app.models_audit import AuditLog
from app.models_booking import Booking
from app.models_candidate import Candidate
from app.models_center import Center
from app.models_session import ExamSession
from app.models_user import User
from app.qr_service import generate_qr_svg
from app.resource_access import assert_booking_access, assert_session_access
from app.schemas import BookingCreate, BookingRead, BookingVerificationRead
from app.sentry import capture_exception as _sentry_cap

router = APIRouter(prefix="/bookings", tags=["bookings"])


def _candidate_for_user(db: Session, current_user: User) -> Candidate | None:
    candidate = db.scalar(select(Candidate).where(Candidate.user_id == current_user.id))
    if not candidate and current_user.email:
        candidate = db.scalar(select(Candidate).where(Candidate.email == current_user.email))
    return candidate


def _notify_booking(db: Session, booking: Booking, candidate: Candidate, session: ExamSession, center: Center) -> None:
    try:
        if candidate.email:
            from app.email_service import send_booking_confirmation

            send_booking_confirmation(
                to_email=candidate.email,
                candidate_name=f"{candidate.first_name} {candidate.last_name}",
                booking_reference=booking.reference,
                session_date=session.starts_at.strftime("%d/%m/%Y à %Hh%M"),
                center_name=center.name,
                verification_code=booking.verification_code,
            )
    except Exception as exc:
        _sentry_cap(exc, context={"endpoint": "booking_confirmation_email"})

    try:
        if candidate.phone:
            from app.orange_sms import send_booking_confirmation_sms

            send_booking_confirmation_sms(
                phone=candidate.phone,
                candidate_name=f"{candidate.first_name} {candidate.last_name}",
                booking_ref=booking.reference,
                session_date=session.starts_at.strftime("%d/%m/%Y %Hh%M"),
                center_name=center.name,
            )
    except Exception as exc:
        _sentry_cap(exc, context={"endpoint": "booking_confirmation_sms"})


@router.get("/my", response_model=list[dict])
def get_my_bookings(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("candidate", "admin", "super_admin")),
) -> list[dict]:
    candidate = _candidate_for_user(db, current_user)
    if not candidate:
        return []

    bookings = db.scalars(
        select(Booking)
        .where(Booking.candidate_id == candidate.id)
        .order_by(Booking.created_at.desc())
        .limit(20)
    ).all()

    session_ids = {booking.session_id for booking in bookings if booking.session_id}
    sessions_by_id: dict[str, ExamSession] = {}
    centers_by_id: dict[str, Center] = {}
    if session_ids:
        sessions = db.scalars(select(ExamSession).where(ExamSession.id.in_(session_ids))).all()
        sessions_by_id = {session.id: session for session in sessions}
        center_ids = {session.center_id for session in sessions if session.center_id}
        if center_ids:
            centers = db.scalars(select(Center).where(Center.id.in_(center_ids))).all()
            centers_by_id = {center.id: center for center in centers}

    return [
        {
            "reference": booking.reference,
            "status": booking.status,
            "verification_code": booking.verification_code,
            "session_date": sessions_by_id[booking.session_id].starts_at.isoformat()
            if booking.session_id in sessions_by_id
            else None,
            "center_name": centers_by_id.get(sessions_by_id[booking.session_id].center_id).name
            if booking.session_id in sessions_by_id
            and centers_by_id.get(sessions_by_id[booking.session_id].center_id)
            else None,
            "center_city": centers_by_id.get(sessions_by_id[booking.session_id].center_id).city
            if booking.session_id in sessions_by_id
            and centers_by_id.get(sessions_by_id[booking.session_id].center_id)
            else None,
        }
        for booking in bookings
    ]


@router.get("", response_model=dict)
def list_bookings(
    candidate_id: str | None = Query(default=None, description="Filtrer par candidat"),
    session_id: str | None = Query(default=None, description="Filtrer par session"),
    booking_status: str | None = Query(default=None, alias="status", description="Statut de réservation"),
    search: str | None = Query(default=None, description="Recherche sur la référence"),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "super_admin", "center")),
) -> dict:
    q = select(Booking).order_by(Booking.created_at.desc())
    if current_user.role == "center":
        if not current_user.center_id:
            q = q.where(Booking.id == "__no_center__")
        else:
            center_session_ids = select(ExamSession.id).where(ExamSession.center_id == current_user.center_id)
            q = q.where(Booking.session_id.in_(center_session_ids))
    if candidate_id:
        q = q.where(Booking.candidate_id == candidate_id)
    if session_id:
        q = q.where(Booking.session_id == session_id)
    if booking_status:
        q = q.where(Booking.status == booking_status)
    if search:
        q = q.where(Booking.reference.ilike(f"%{search}%"))
    total = db.scalar(select(func.count()).select_from(q.subquery())) or 0
    raw_items = list(db.scalars(q.offset(offset).limit(limit)).all())
    items = [BookingRead.model_validate(item) for item in raw_items]
    return {"items": items, "total": total, "limit": limit, "offset": offset, "search": search}


@router.post("", response_model=BookingRead, status_code=status.HTTP_201_CREATED)
def create_booking(
    payload: BookingCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "super_admin", "center")),
) -> Booking:
    candidate = db.get(Candidate, payload.candidate_id)
    if not candidate:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidat introuvable")
    session, center = lock_bookable_session(db, payload.session_id)
    assert_session_access(current_user, session)
    assert_no_active_booking(db, candidate.id)
    assert_session_has_capacity(db, session)

    acquire_booking_reference_lock(db)
    sequence_number = (db.scalar(select(func.count(Booking.id))) or 0) + 1
    reference = build_booking_reference(sequence_number)
    booking = Booking(
        reference=reference,
        candidate_id=candidate.id,
        session_id=session.id,
        verification_code=build_verification_code(reference),
        status="confirmed",
    )
    db.add(booking)
    db.flush()
    db.add(
        AuditLog(
            actor_id=current_user.id,
            action="booking.created",
            entity="booking",
            entity_id=booking.id,
            details={
                "reference": booking.reference,
                "candidate_id": candidate.id,
                "session_id": session.id,
                "center_id": center.id,
            },
        )
    )
    db.commit()
    db.refresh(booking)
    _notify_booking(db, booking, candidate, session, center)
    return booking


@router.get("/{reference}", response_model=BookingRead)
def get_booking(
    reference: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Booking:
    booking = db.scalar(select(Booking).where(Booking.reference == reference))
    if not booking:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found")
    assert_booking_access(db, current_user, booking)
    return booking


@router.get("/{reference}/convocation")
def get_convocation(
    reference: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    booking = db.scalar(select(Booking).where(Booking.reference == reference))
    if not booking:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found")
    assert_booking_access(db, current_user, booking)
    candidate = db.get(Candidate, booking.candidate_id)
    session = db.get(ExamSession, booking.session_id)
    center = db.get(Center, session.center_id) if session else None
    if not candidate or not session or not center:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Incomplete booking data")
    return build_convocation_payload(booking, candidate, session, center)


@router.get("/{reference}/convocation/qr.svg")
def get_convocation_qr(
    reference: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    booking = db.scalar(select(Booking).where(Booking.reference == reference))
    if not booking:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found")
    assert_booking_access(db, current_user, booking)
    svg = generate_qr_svg(f"CODEROUTE-GN|REF={booking.reference}|VERIFY={booking.verification_code}")
    return Response(content=svg, media_type="image/svg+xml")


@router.post("/{reference}/cancel", response_model=BookingRead)
def cancel_booking(
    reference: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Booking:
    booking = db.scalar(select(Booking).where(Booking.reference == reference).with_for_update())
    if not booking:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found")
    assert_booking_access(db, current_user, booking)
    if booking.status == "cancelled":
        return booking
    if booking.status in {"paid", "checked_in"}:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cette réservation a déjà été payée ou enregistrée au centre. Utilisez le workflow de remboursement/annulation assistée.",
        )

    booking.status = "cancelled"
    booking.cancelled_at = datetime.now(UTC).replace(tzinfo=None)
    booking.notes = ((booking.notes or "") + " | Annulation demandée par l'utilisateur").strip(" |")
    db.add(booking)
    db.add(
        AuditLog(
            actor_id=current_user.id,
            action="booking.cancelled",
            entity="booking",
            entity_id=booking.id,
            details={"reference": booking.reference, "previous_status": "confirmed"},
        )
    )
    db.commit()
    db.refresh(booking)
    return booking


@router.get("/verify/{verification_code}", response_model=BookingVerificationRead)
def verify_booking(verification_code: str, db: Session = Depends(get_db)) -> BookingVerificationRead:
    booking = db.scalar(select(Booking).where(Booking.verification_code == verification_code))
    if not booking:
        return BookingVerificationRead(valid=False)
    return BookingVerificationRead(valid=True, reference=booking.reference, status=booking.status)


@router.get("/availability/{center_id}", response_model=dict)
def get_center_availability(
    center_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    center = db.get(Center, center_id)
    if not center:
        raise HTTPException(status_code=404, detail="Centre introuvable")
    if center.status not in {"active", "accredited"}:
        raise HTTPException(status_code=409, detail="Ce centre n'est pas actuellement disponible pour les réservations.")

    now = datetime.now(UTC).replace(tzinfo=None)
    sessions = db.scalars(
        select(ExamSession)
        .where(
            ExamSession.center_id == center_id,
            ExamSession.starts_at > now,
            ExamSession.status.in_(["planned", "open"]),
        )
        .order_by(ExamSession.starts_at.asc())
        .limit(30)
    ).all()

    session_ids = [session.id for session in sessions]
    booked_by_session: dict[str, int] = {}
    if session_ids:
        rows = db.execute(
            select(Booking.session_id, func.count(Booking.id))
            .where(
                Booking.session_id.in_(session_ids),
                Booking.status.not_in(["cancelled"]),
            )
            .group_by(Booking.session_id)
        ).all()
        booked_by_session = {session_id: count for session_id, count in rows}

    items = []
    for session in sessions:
        booked = booked_by_session.get(session.id, 0)
        remaining = max(0, session.capacity - booked)
        items.append(
            {
                "session_id": session.id,
                "reference": session.reference,
                "starts_at": session.starts_at.isoformat(),
                "capacity": session.capacity,
                "booked": booked,
                "remaining_seats": remaining,
                "full": remaining == 0,
            }
        )

    return {
        "center": {
            "id": center.id,
            "name": center.name,
            "city": center.city,
            "commune": center.commune,
            "address": center.address,
        },
        "sessions": items,
    }


class SelfBookingCreate(BaseModel):
    session_id: str


@router.post("/self", response_model=BookingRead, status_code=status.HTTP_201_CREATED)
def create_self_booking(
    payload: SelfBookingCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("candidate")),
) -> Booking:
    candidate = _candidate_for_user(db, current_user)
    if not candidate:
        raise HTTPException(status_code=404, detail="Aucune fiche candidat liée à ce compte. Complétez votre inscription.")

    session, center = lock_bookable_session(db, payload.session_id)
    assert_no_active_booking(db, candidate.id)
    assert_session_has_capacity(db, session)

    acquire_booking_reference_lock(db)
    sequence_number = (db.scalar(select(func.count(Booking.id))) or 0) + 1
    reference = build_booking_reference(sequence_number)
    booking = Booking(
        reference=reference,
        candidate_id=candidate.id,
        session_id=session.id,
        verification_code=build_verification_code(reference),
        status="confirmed",
        notes="Réservation en ligne — paiement requis avant l'enregistrement au centre",
    )
    db.add(booking)
    db.flush()
    db.add(
        AuditLog(
            actor_id=current_user.id,
            action="booking.self_created",
            entity="booking",
            entity_id=booking.id,
            details={"reference": booking.reference, "session_id": session.id, "center_id": center.id},
        )
    )
    db.commit()
    db.refresh(booking)
    _notify_booking(db, booking, candidate, session, center)
    return booking
