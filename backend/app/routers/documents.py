from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.convocation_service import build_convocation_payload
from app.db.session import get_db
from app.models_booking import Booking
from app.models_candidate import Candidate
from app.models_center import Center
from app.models_session import ExamSession
from app.pdf_service import build_convocation_pdf

router = APIRouter(prefix="/documents", tags=["documents"])


@router.get("/convocations/{reference}.pdf")
def get_convocation_pdf(reference: str, db: Session = Depends(get_db)) -> Response:
    booking = db.scalar(select(Booking).where(Booking.reference == reference))
    if not booking:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found")
    candidate = db.get(Candidate, booking.candidate_id)
    session = db.get(ExamSession, booking.session_id)
    center = db.get(Center, session.center_id) if session else None
    if not candidate or not session or not center:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Incomplete booking data")
    convocation = build_convocation_payload(booking, candidate, session, center)
    headers = {"Content-Disposition": f"attachment; filename=coderoute-convocation-{booking.reference}.pdf"}
    return Response(content=build_convocation_pdf(convocation), media_type="application/pdf", headers=headers)
