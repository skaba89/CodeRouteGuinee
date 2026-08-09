from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.audit_chain import verify_audit_chain
from app.db.session import get_db
from app.deps import require_roles
from app.models_audit import AuditLog
from app.models_center_incident import CenterIncident
from app.models_device_session import DeviceSession
from app.models_user import User
from app.soc_config import get_soc_settings

router = APIRouter(prefix="/operations/security", tags=["security-operations"])


def _count_action(db: Session, action: str, since: datetime) -> int:
    return int(
        db.scalar(
            select(func.count(AuditLog.id)).where(
                AuditLog.action == action,
                AuditLog.created_at >= since.replace(tzinfo=None),
            )
        )
        or 0
    )


@router.get("/status")
def security_status(
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_roles("admin", "super_admin")),
) -> dict:
    now = datetime.now(UTC)
    since_15m = now - timedelta(minutes=15)
    since_24h = now - timedelta(hours=24)

    login_failed_15m = _count_action(db, "auth.login_failed", since_15m)
    login_blocked_15m = _count_action(db, "auth.login_blocked", since_15m)
    login_failed_24h = _count_action(db, "auth.login_failed", since_24h)

    suspicious_devices = int(
        db.scalar(select(func.count(DeviceSession.id)).where(DeviceSession.status == "suspicious")) or 0
    )
    critical_incidents = int(
        db.scalar(
            select(func.count(CenterIncident.id)).where(
                CenterIncident.status == "open",
                CenterIncident.severity.in_(["high", "critical"]),
            )
        )
        or 0
    )

    audit = verify_audit_chain(db)
    alerts: list[dict] = []
    if not audit.get("valid", False):
        alerts.append({"code": "AUDIT_CHAIN_INVALID", "severity": "critical"})
    if login_blocked_15m > 0 or login_failed_15m >= 10:
        alerts.append({"code": "AUTH_BRUTE_FORCE_SIGNAL", "severity": "warning"})
    if suspicious_devices > 0:
        alerts.append({"code": "SUSPICIOUS_DEVICE", "severity": "warning"})
    if critical_incidents > 0:
        alerts.append({"code": "CRITICAL_CENTER_INCIDENT", "severity": "critical"})

    critical = any(item["severity"] == "critical" for item in alerts)
    warning = any(item["severity"] == "warning" for item in alerts)
    status = "critical" if critical else "warning" if warning else "ok"

    return {
        "status": status,
        "generated_at": now.isoformat(),
        "soc_policy": get_soc_settings().safe_policy(),
        "audit_chain": audit,
        "signals": {
            "login_failed_15m": login_failed_15m,
            "login_blocked_15m": login_blocked_15m,
            "login_failed_24h": login_failed_24h,
            "suspicious_devices": suspicious_devices,
            "critical_center_incidents": critical_incidents,
        },
        "alerts": alerts,
    }
