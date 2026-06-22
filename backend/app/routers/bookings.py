from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.booking_service import build_booking_reference, build_verification_code
from app.convocation_service import build_convocation_payload
from app.db.session import get_db
from app.deps import get_current_user, require_roles
from app.models_booking import Booking
from app.models_candidate import Candidate
from app.models_center import Center
from app.models_session import ExamSession
from app.models_user import User
from app.qr_service import generate_qr_svg
from app.schemas import BookingCreate, BookingRead, BookingVerificationRead

router = APIRouter(prefix="/bookings", tags=["bookings"])


@router.get("", response_model=dict)
def list_bookings(
    candidate_id: str | None = Query(default=None, description="Filtrer par candidat"),
    session_id: str | None = Query(default=None, description="Filtrer par session"),
    booking_status: str | None = Query(default=None, alias="status", description="Statut : pending | confirmed | cancelled"),
    search: str | None = Query(default=None, description="Recherche sur la référence"),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "super_admin", "center")),
) -> list[Booking]:
    q = select(Booking).order_by(Booking.created_at.desc())
    if candidate_id:
        q = q.where(Booking.candidate_id == candidate_id)
    if session_id:
        q = q.where(Booking.session_id == session_id)
    if booking_status:
        q = q.where(Booking.status == booking_status)
    if search:
        q = q.where(Booking.reference.ilike(f"%{search}%"))
    total = db.scalar(select(func.count()).select_from(q.subquery()))
    raw_items = list(db.scalars(q.offset(offset).limit(limit)).all())
    items = [BookingRead.model_validate(x) for x in raw_items]
    return {"items": items, "total": total, "limit": limit, "offset": offset, "search": search}


@router.post("", response_model=BookingRead, status_code=status.HTTP_201_CREATED)
def create_booking(
    payload: BookingCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "super_admin", "center")),
) -> Booking:
    sequence_number = db.query(Booking).count() + 1
    reference = build_booking_reference(sequence_number)
    booking = Booking(
        reference=reference,
        candidate_id=payload.candidate_id,
        session_id=payload.session_id,
        verification_code=build_verification_code(reference),
    )
    db.add(booking)
    db.commit()
    db.refresh(booking)
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
    svg = generate_qr_svg(f"CODEROUTE-GN|REF={booking.reference}|VERIFY={booking.verification_code}")
    return Response(content=svg, media_type="image/svg+xml")


@router.get("/verify/{verification_code}", response_model=BookingVerificationRead)
def verify_booking(verification_code: str, db: Session = Depends(get_db)) -> BookingVerificationRead:
    booking = db.scalar(select(Booking).where(Booking.verification_code == verification_code))
    if not booking:
        return BookingVerificationRead(valid=False)
    return BookingVerificationRead(valid=True, reference=booking.reference, status=booking.status)
