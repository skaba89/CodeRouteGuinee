from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.deps import require_roles
from app.models_audit import AuditLog
from app.models_center import Center
from app.models_center_incident import CenterIncident
from app.models_exam_attempt import ExamAttempt
from app.models_session import ExamSession
from app.models_user import User
from app.schemas import CenterIncidentCreate, CenterIncidentRead, CenterIncidentResolveRequest

router = APIRouter(prefix="/center-incidents", tags=["center-incidents"])


@router.post("", response_model=CenterIncidentRead, status_code=status.HTTP_201_CREATED)
def report_center_incident(
    payload: CenterIncidentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("center", "admin", "super_admin")),
) -> CenterIncident:
    center = db.get(Center, payload.center_id)
    if not center:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Center not found")

    session = db.get(ExamSession, payload.session_id) if payload.session_id else None
    if payload.session_id and not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exam session not found")
    if session and session.center_id != center.id:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Session does not belong to this center")

    attempt = db.get(ExamAttempt, payload.attempt_id) if payload.attempt_id else None
    if payload.attempt_id and not attempt:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exam attempt not found")
    if attempt and session and attempt.session_id != session.id:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Attempt does not belong to this session")

    incident = CenterIncident(
        center_id=center.id,
        session_id=session.id if session else None,
        attempt_id=attempt.id if attempt else None,
        incident_type=payload.incident_type,
        severity=payload.severity,
        description=payload.description,
        reported_by_id=current_user.id,
    )

    if attempt and attempt.status == "started":
        attempt.status = "incident_blocked"
        db.add(attempt)

    db.add(incident)
    db.flush()
    db.add(
        AuditLog(
            actor_id=current_user.id,
            action="center_incident.reported",
            entity="center_incident",
            entity_id=incident.id,
            details={
                "center_id": center.id,
                "center_code": center.code,
                "session_id": session.id if session else None,
                "attempt_id": attempt.id if attempt else None,
                "incident_type": incident.incident_type,
                "severity": incident.severity,
                "attempt_status_after_report": attempt.status if attempt else None,
            },
        )
    )
    db.commit()
    db.refresh(incident)
    return incident


@router.get("", response_model=list[CenterIncidentRead])
def list_center_incidents(
    status_filter: str | None = None,
    center_id: str | None = None,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "super_admin")),
) -> list[CenterIncident]:
    query = select(CenterIncident).order_by(CenterIncident.created_at.desc()).limit(limit)
    if status_filter:
        query = query.where(CenterIncident.status == status_filter)
    if center_id:
        query = query.where(CenterIncident.center_id == center_id)
    return list(db.scalars(query).all())


@router.post("/{incident_id}/resolve", response_model=CenterIncidentRead)
def resolve_center_incident(
    incident_id: str,
    payload: CenterIncidentResolveRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "super_admin")),
) -> CenterIncident:
    incident = db.get(CenterIncident, incident_id)
    if not incident:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Center incident not found")
    if incident.status == "resolved":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Center incident already resolved")

    now = datetime.utcnow()
    attempt = db.get(ExamAttempt, incident.attempt_id) if incident.attempt_id else None
    new_attempt = None

    if payload.allow_retake and attempt:
        if attempt.status not in {"incident_blocked", "started", "expired"}:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Attempt is not eligible for retake")
        attempt.status = "cancelled_by_incident"
        attempt.submitted_at = now
        new_attempt = ExamAttempt(candidate_id=attempt.candidate_id, session_id=attempt.session_id)
        db.add(attempt)
        db.add(new_attempt)
        db.flush()
        incident.new_attempt_id = new_attempt.id
    elif attempt and attempt.status == "incident_blocked":
        attempt.status = "cancelled_by_incident"
        attempt.submitted_at = now
        db.add(attempt)

    incident.status = "resolved"
    incident.resolution_notes = payload.resolution_notes
    incident.resolved_by_id = current_user.id
    incident.resolved_at = now
    db.add(incident)
    db.add(
        AuditLog(
            actor_id=current_user.id,
            action="center_incident.resolved",
            entity="center_incident",
            entity_id=incident.id,
            details={
                "center_id": incident.center_id,
                "session_id": incident.session_id,
                "attempt_id": incident.attempt_id,
                "allow_retake": payload.allow_retake,
                "new_attempt_id": incident.new_attempt_id,
                "resolution_notes": payload.resolution_notes,
            },
        )
    )
    db.commit()
    db.refresh(incident)
    return incident
