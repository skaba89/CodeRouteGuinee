"""Fail-closed eligibility facade for official exam start endpoints.

The historical exam router still owns trace creation, station checks, retry
semantics and audit. This facade adds one missing invariant at the boundary:
an official attempt cannot be created/resumed for an ineligible candidate.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.candidate_eligibility import assert_candidate_ready_for_official_exam
from app.db.session import get_db
from app.deps import require_roles
from app.models_booking import Booking
from app.models_candidate import Candidate
from app.models_user import User
from app.resource_access import assert_booking_access
from app.routers import exams as legacy_exams
from app.schemas import ExamAttemptRead, ExamStartFromBookingRequest, ExamStartRequest

router = APIRouter(prefix="/exams", tags=["exams"])


def _locked_eligible_candidate(db: Session, candidate_id: str) -> Candidate:
    candidate = db.scalar(
        select(Candidate)
        .where(Candidate.id == candidate_id)
        .with_for_update()
    )
    if not candidate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "EXAM_CANDIDATE_NOT_FOUND", "message": "Candidat introuvable."},
        )
    assert_candidate_ready_for_official_exam(candidate)
    return candidate


@router.post("/start", response_model=ExamAttemptRead, status_code=status.HTTP_201_CREATED)
def start_exam_with_eligibility(
    payload: ExamStartRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "super_admin")),
):
    # Même l'override administratif ne doit pas fabriquer une tentative
    # officielle pour un dossier suspendu/non vérifié. Les exceptions futures
    # devront être un workflow institutionnel explicite et audité.
    _locked_eligible_candidate(db, payload.candidate_id)
    return legacy_exams.start_exam(payload=payload, db=db, current_user=current_user)


@router.post("/start-from-booking", response_model=ExamAttemptRead, status_code=status.HTTP_201_CREATED)
def start_exam_from_booking_with_eligibility(
    payload: ExamStartFromBookingRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("candidate", "center", "admin", "super_admin")),
):
    booking = db.scalar(
        select(Booking).where(Booking.reference == payload.booking_reference)
    )
    if booking is None:
        # Délègue au routeur historique pour conserver exactement son contrat 404.
        return legacy_exams.start_exam_from_booking(payload=payload, db=db, current_user=current_user)

    # Vérifier le périmètre avant l'éligibilité évite de révéler l'état d'un
    # candidat à un utilisateur qui aurait deviné une référence de réservation.
    assert_booking_access(db, current_user, booking)

    # Avant check-in, le routeur historique doit continuer à répondre
    # CHECKIN_REQUIRED_BEFORE_EXAM. Dès que le dossier porte checked_in, on
    # verrouille le candidat afin qu'une suspension concurrente ne puisse pas
    # passer entre le contrôle et la création/reprise de tentative.
    if booking.status == "checked_in":
        _locked_eligible_candidate(db, booking.candidate_id)

    return legacy_exams.start_exam_from_booking(payload=payload, db=db, current_user=current_user)
