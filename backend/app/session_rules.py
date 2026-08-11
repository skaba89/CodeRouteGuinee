from __future__ import annotations

from datetime import timedelta

from fastapi import HTTPException, status
from sqlalchemy import and_, func, select, text
from sqlalchemy.orm import Session

from app.models_center import Center
from app.models_session import ExamSession

# Paramètres opérationnels courants. Ils restent configurables/à homologuer
# formellement par l'autorité compétente avant d'être qualifiés de norme DNTT.
MAX_CAPACITY = 35
MAX_SESSIONS_PER_WEEK = 3
SESSION_DURATION_HOURS = 2
_SESSION_REFERENCE_LOCK_ID = 2026081103
_OPERATIONAL_CENTER_STATUSES = {"active", "accredited"}


def acquire_session_reference_lock(db: Session) -> None:
    if db.get_bind().dialect.name == "postgresql":
        db.execute(text("SELECT pg_advisory_xact_lock(:lock_id)"), {"lock_id": _SESSION_REFERENCE_LOCK_ID})


def lock_operational_center(db: Session, center_id: str) -> Center:
    center = db.scalar(select(Center).where(Center.id == center_id).with_for_update())
    if not center:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Centre introuvable")
    if center.status not in _OPERATIONAL_CENTER_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Le centre '{center.name}' n'est pas opérationnel (statut: {center.status}).",
        )
    return center


def count_sessions_this_week(db: Session, center_id: str, starts_at) -> int:
    week_start = starts_at - timedelta(days=starts_at.weekday())
    week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)
    week_end = week_start + timedelta(days=7)
    return db.scalar(
        select(func.count(ExamSession.id)).where(
            and_(
                ExamSession.center_id == center_id,
                ExamSession.starts_at >= week_start,
                ExamSession.starts_at < week_end,
                ExamSession.status.not_in(["cancelled", "archived"]),
            )
        )
    ) or 0


def has_overlapping_session(
    db: Session,
    center_id: str,
    starts_at,
    exclude_id: str | None = None,
) -> bool:
    window_start = starts_at - timedelta(hours=SESSION_DURATION_HOURS)
    window_end = starts_at + timedelta(hours=SESSION_DURATION_HOURS)
    query = select(ExamSession.id).where(
        and_(
            ExamSession.center_id == center_id,
            ExamSession.starts_at > window_start,
            ExamSession.starts_at < window_end,
            ExamSession.status.not_in(["cancelled", "archived"]),
        )
    )
    if exclude_id:
        query = query.where(ExamSession.id != exclude_id)
    return db.scalar(query) is not None


def validate_session_slot(db: Session, center: Center, starts_at, capacity: int) -> None:
    if capacity > MAX_CAPACITY:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"La capacité opérationnelle maximale est de {MAX_CAPACITY} candidats par session.",
        )
    effective_max = min(center.max_sessions_per_week, MAX_SESSIONS_PER_WEEK)
    sessions_this_week = count_sessions_this_week(db, center.id, starts_at)
    if sessions_this_week >= effective_max:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"Ce centre a déjà {sessions_this_week} session(s) planifiée(s) cette semaine. "
                f"Maximum opérationnel courant : {effective_max}."
            ),
        )
    if has_overlapping_session(db, center.id, starts_at):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Une session existe déjà dans la fenêtre opérationnelle de {SESSION_DURATION_HOURS}h.",
        )
