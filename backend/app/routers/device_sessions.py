from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.deps import require_roles
from app.models_audit import AuditLog
from app.models_center import Center
from app.models_device_session import DeviceSession
from app.models_exam_attempt import ExamAttempt
from app.models_session import ExamSession
from app.models_user import User
from app.schemas import DeviceSessionHeartbeat, DeviceSessionRead

router = APIRouter(prefix="/device-sessions", tags=["device-sessions"])


@router.post("/heartbeat", response_model=DeviceSessionRead, status_code=status.HTTP_201_CREATED)
def register_device_heartbeat(
    payload: DeviceSessionHeartbeat,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("center", "admin", "super_admin")),
) -> DeviceSession:
    center = db.get(Center, payload.center_id)
    if not center:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Center not found")

    session = db.get(ExamSession, payload.session_id)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exam session not found")
    if session.center_id != center.id:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Session does not belong to this center")

    attempt = db.get(ExamAttempt, payload.attempt_id) if payload.attempt_id else None
    if payload.attempt_id and not attempt:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exam attempt not found")
    if attempt and attempt.session_id != session.id:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Attempt does not belong to this session")

    now = datetime.utcnow()
    existing = db.scalar(
        select(DeviceSession).where(
            DeviceSession.center_id == center.id,
            DeviceSession.session_id == session.id,
            DeviceSession.device_key == payload.device_key,
            DeviceSession.attempt_id == payload.attempt_id,
        )
    )
    if existing:
        existing.device_label = payload.device_label or existing.device_label
        existing.ip_address = payload.ip_address or existing.ip_address
        existing.user_agent = payload.user_agent or existing.user_agent
        existing.last_seen_at = now
        db.add(existing)
        db.commit()
        db.refresh(existing)
        return existing

    duplicate = db.scalar(
        select(DeviceSession).where(
            DeviceSession.center_id == center.id,
            DeviceSession.session_id == session.id,
            DeviceSession.device_key == payload.device_key,
            DeviceSession.status.in_(["active", "suspicious"]),
        )
    )
    status_label = "active"
    risk_reason = None
    if duplicate and duplicate.attempt_id != payload.attempt_id:
        duplicate.status = "suspicious"
        duplicate.risk_reason = "same_device_key_used_for_multiple_attempts"
        duplicate.last_seen_at = now
        status_label = "suspicious"
        risk_reason = "same_device_key_used_for_multiple_attempts"
        db.add(duplicate)

    device_session = DeviceSession(
        center_id=center.id,
        session_id=session.id,
        attempt_id=payload.attempt_id,
        device_key=payload.device_key,
        device_label=payload.device_label,
        ip_address=payload.ip_address,
        user_agent=payload.user_agent,
        status=status_label,
        risk_reason=risk_reason,
        last_seen_at=now,
    )
    db.add(device_session)
    db.flush()

    action = "device_session.heartbeat"
    if status_label == "suspicious":
        action = "device_session.suspicious_duplicate"
    db.add(
        AuditLog(
            actor_id=current_user.id,
            action=action,
            entity="device_session",
            entity_id=device_session.id,
            details={
                "center_id": center.id,
                "center_code": center.code,
                "session_id": session.id,
                "attempt_id": payload.attempt_id,
                "device_key": payload.device_key,
                "status": status_label,
                "risk_reason": risk_reason,
                "duplicate_device_session_id": duplicate.id if duplicate else None,
            },
        )
    )
    db.commit()
    db.refresh(device_session)
    return device_session


@router.get("", response_model=list[DeviceSessionRead])
def list_device_sessions(
    session_id: str | None = None,
    center_id: str | None = None,
    status_filter: str | None = None,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "super_admin")),
) -> list[DeviceSession]:
    query = select(DeviceSession)
    if session_id:
        query = query.where(DeviceSession.session_id == session_id)
    if center_id:
        query = query.where(DeviceSession.center_id == center_id)
    if status_filter:
        query = query.where(DeviceSession.status == status_filter)
    query = query.order_by(DeviceSession.last_seen_at.desc()).limit(limit)
    return list(db.scalars(query).all())


@router.get("/alerts", response_model=list[DeviceSessionRead])
def list_device_session_alerts(
    session_id: str | None = None,
    center_id: str | None = None,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "super_admin")),
) -> list[DeviceSession]:
    query = select(DeviceSession).where(DeviceSession.status == "suspicious")
    if session_id:
        query = query.where(DeviceSession.session_id == session_id)
    if center_id:
        query = query.where(DeviceSession.center_id == center_id)
    query = query.order_by(DeviceSession.last_seen_at.desc()).limit(limit)
    return list(db.scalars(query).all())
