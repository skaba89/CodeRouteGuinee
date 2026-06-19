from datetime import datetime
from app.time_utils import utc_now

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.deps import require_roles
from app.models_audit import AuditLog
from app.models_center import Center
from app.models_exam_attempt import ExamAttempt
from app.models_exam_monitoring import ExamMonitoringEvent
from app.models_session import ExamSession
from app.models_user import User

router = APIRouter(prefix="/exam-monitoring", tags=["exam-monitoring"])

SEVERITY_SCORES = {
    "low": 1,
    "medium": 3,
    "high": 7,
    "critical": 12,
}


class ExamMonitoringEventCreate(BaseModel):
    attempt_id: str
    event_type: str = Field(min_length=3)
    severity: str = "low"
    details: dict | None = None
    occurred_at: datetime | None = None


class ExamMonitoringEventRead(BaseModel):
    id: str
    center_id: str | None = None
    session_id: str
    attempt_id: str
    event_type: str
    severity: str
    risk_score: int
    details: dict | None = None
    reported_by_id: str | None = None
    occurred_at: datetime
    created_at: datetime

    model_config = {"from_attributes": True}


class ExamMonitoringSummary(BaseModel):
    attempt_id: str
    total_events: int
    total_risk_score: int
    max_severity: str
    status: str


def normalize_severity(severity: str) -> str:
    value = severity.lower().strip()
    if value not in SEVERITY_SCORES:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid severity")
    return value


def build_status(total_risk_score: int) -> str:
    if total_risk_score >= 20:
        return "critical_review"
    if total_risk_score >= 10:
        return "manual_review"
    if total_risk_score >= 4:
        return "watch"
    return "normal"


@router.post("/events", response_model=ExamMonitoringEventRead, status_code=status.HTTP_201_CREATED)
def create_monitoring_event(
    payload: ExamMonitoringEventCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("center", "admin", "super_admin")),
) -> ExamMonitoringEvent:
    attempt = db.get(ExamAttempt, payload.attempt_id)
    if not attempt:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exam attempt not found")

    session = db.get(ExamSession, attempt.session_id)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exam session not found")

    center = db.get(Center, session.center_id)
    severity = normalize_severity(payload.severity)
    risk_score = SEVERITY_SCORES[severity]
    occurred_at = payload.occurred_at or utc_now()

    event = ExamMonitoringEvent(
        center_id=center.id if center else None,
        session_id=session.id,
        attempt_id=attempt.id,
        event_type=payload.event_type,
        severity=severity,
        risk_score=risk_score,
        details=payload.details,
        reported_by_id=current_user.id,
        occurred_at=occurred_at,
    )
    db.add(event)
    db.flush()

    action = "exam_monitoring.event_recorded"
    if severity in {"high", "critical"}:
        action = "exam_monitoring.high_risk_event"
    db.add(
        AuditLog(
            actor_id=current_user.id,
            action=action,
            entity="exam_monitoring_event",
            entity_id=event.id,
            details={
                "attempt_id": attempt.id,
                "session_id": session.id,
                "center_id": center.id if center else None,
                "event_type": payload.event_type,
                "severity": severity,
                "risk_score": risk_score,
            },
        )
    )
    db.commit()
    db.refresh(event)
    return event


@router.get("/events", response_model=list[ExamMonitoringEventRead])
def list_monitoring_events(
    attempt_id: str | None = None,
    session_id: str | None = None,
    severity: str | None = None,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "super_admin")),
) -> list[ExamMonitoringEvent]:
    query = select(ExamMonitoringEvent)
    if attempt_id:
        query = query.where(ExamMonitoringEvent.attempt_id == attempt_id)
    if session_id:
        query = query.where(ExamMonitoringEvent.session_id == session_id)
    if severity:
        query = query.where(ExamMonitoringEvent.severity == normalize_severity(severity))
    query = query.order_by(ExamMonitoringEvent.occurred_at.desc()).limit(limit)
    return list(db.scalars(query).all())


@router.get("/attempts/{attempt_id}/summary", response_model=ExamMonitoringSummary)
def get_attempt_monitoring_summary(
    attempt_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "super_admin")),
) -> ExamMonitoringSummary:
    attempt = db.get(ExamAttempt, attempt_id)
    if not attempt:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exam attempt not found")

    events = list(db.scalars(select(ExamMonitoringEvent).where(ExamMonitoringEvent.attempt_id == attempt_id)).all())
    total_risk_score = sum(event.risk_score for event in events)
    max_score = max((event.risk_score for event in events), default=0)
    max_severity = "none"
    for severity, score in SEVERITY_SCORES.items():
        if score == max_score:
            max_severity = severity
            break

    return ExamMonitoringSummary(
        attempt_id=attempt_id,
        total_events=len(events),
        total_risk_score=total_risk_score,
        max_severity=max_severity,
        status=build_status(total_risk_score),
    )


@router.get("/summary", response_model=list[ExamMonitoringSummary])
def list_monitoring_summaries(
    session_id: str | None = None,
    min_risk_score: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "super_admin")),
) -> list[ExamMonitoringSummary]:
    query = select(
        ExamMonitoringEvent.attempt_id,
        func.count(ExamMonitoringEvent.id).label("total_events"),
        func.sum(ExamMonitoringEvent.risk_score).label("total_risk_score"),
    )
    if session_id:
        query = query.where(ExamMonitoringEvent.session_id == session_id)
    query = query.group_by(ExamMonitoringEvent.attempt_id).having(func.sum(ExamMonitoringEvent.risk_score) >= min_risk_score).limit(limit)

    summaries: list[ExamMonitoringSummary] = []
    for attempt_id, total_events, total_risk_score in db.execute(query).all():
        total = int(total_risk_score or 0)
        event_scores = list(db.scalars(select(ExamMonitoringEvent.risk_score).where(ExamMonitoringEvent.attempt_id == attempt_id)).all())
        max_score = max(event_scores, default=0)
        max_severity = "none"
        for severity, score in SEVERITY_SCORES.items():
            if score == max_score:
                max_severity = severity
                break
        summaries.append(
            ExamMonitoringSummary(
                attempt_id=attempt_id,
                total_events=int(total_events or 0),
                total_risk_score=total,
                max_severity=max_severity,
                status=build_status(total),
            )
        )
    return summaries
