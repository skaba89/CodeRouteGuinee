from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
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
