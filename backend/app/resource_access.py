from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models_booking import Booking
from app.models_candidate import Candidate
from app.models_session import ExamSession
from app.models_user import User

_ADMIN_ROLES = {"admin", "super_admin"}


def assert_session_access(current_user: User, session: ExamSession) -> None:
    if current_user.role in _ADMIN_ROLES:
        return
    if current_user.role == "center" and current_user.center_id and session.center_id == current_user.center_id:
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cette session appartient à un autre centre.")


def assert_candidate_access(db: Session, current_user: User, candidate: Candidate) -> None:
    if current_user.role in _ADMIN_ROLES:
        return
    if current_user.role == "candidate":
        if candidate.user_id == current_user.id or bool(candidate.email and candidate.email == current_user.email):
            return
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Ce dossier candidat ne vous appartient pas.")
    if current_user.role == "driving_school":
        if candidate.registered_by == current_user.id:
            return
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Ce candidat n'appartient pas à votre auto-école.")
    if current_user.role == "center" and current_user.center_id:
        accessible = db.scalar(
            select(Booking.id)
            .join(ExamSession, Booking.session_id == ExamSession.id)
            .where(
                Booking.candidate_id == candidate.id,
                ExamSession.center_id == current_user.center_id,
            )
            .limit(1)
        )
        if accessible:
            return
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Ce candidat n'est pas rattaché à votre centre.")
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Accès candidat refusé.")


def assert_booking_access(db: Session, current_user: User, booking: Booking) -> None:
    if current_user.role in _ADMIN_ROLES:
        return
    candidate = db.get(Candidate, booking.candidate_id)
    if current_user.role == "candidate":
        if candidate and (candidate.user_id == current_user.id or bool(candidate.email and candidate.email == current_user.email)):
            return
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cette réservation ne vous appartient pas.")
    if current_user.role == "driving_school":
        if candidate and candidate.registered_by == current_user.id:
            return
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cette réservation n'appartient pas à votre auto-école.")
    if current_user.role == "center" and current_user.center_id:
        session = db.get(ExamSession, booking.session_id)
        if session and session.center_id == current_user.center_id:
            return
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cette réservation appartient à un autre centre.")
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Accès réservation refusé.")
