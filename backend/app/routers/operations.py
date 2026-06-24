from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.deps import require_roles
from app.models_audit import AuditLog
from app.models_center_incident import CenterIncident
from app.models_device_session import DeviceSession
from app.models_exam_monitoring import ExamMonitoringEvent
from app.models_payment import Payment
from app.models_user import User

router = APIRouter(prefix="/operations", tags=["operations"])


class OperationAlert(BaseModel):
    code: str
    label: str
    severity: str
    count: int
    target: str


class OperationsSummaryRead(BaseModel):
    status: str
    generated_at: datetime
    critical_alerts: int
    warning_alerts: int
    open_incidents: int
    critical_incidents: int
    high_risk_exam_events: int
    critical_exam_events: int
    suspicious_devices: int
    payment_alerts: int
    audit_events_24h: int
    last_audit_at: datetime | None = None
    alerts: list[OperationAlert]


def _severity(count: int, warning: int, critical: int) -> str:
    if count >= critical:
        return "critical"
    if count >= warning:
        return "warning"
    return "ok"


def _alert(code: str, label: str, count: int, target: str, warning: int, critical: int) -> OperationAlert | None:
    severity = _severity(count, warning, critical)
    if severity == "ok":
        return None
    return OperationAlert(code=code, label=label, severity=severity, count=count, target=target)


def _count_payment_alerts(db: Session) -> int:
    payments = db.scalars(select(Payment)).all()
    booking_counts: dict[str, int] = {}
    receipt_counts: dict[str, int] = {}
    for payment in payments:
        booking_counts[payment.booking_reference] = booking_counts.get(payment.booking_reference, 0) + 1
        receipt_counts[payment.receipt_number] = receipt_counts.get(payment.receipt_number, 0) + 1

    alerts = 0
    for payment in payments:
        if payment.status in {"failed", "pending"}:
            alerts += 1
        if payment.amount_gnf <= 0 or payment.amount_gnf > 1_000_000:
            alerts += 1
        if booking_counts.get(payment.booking_reference, 0) > 1:
            alerts += 1
        if receipt_counts.get(payment.receipt_number, 0) > 1:
            alerts += 1
    return alerts


def _build_operations_summary(db: Session) -> OperationsSummaryRead:
    now = datetime.now(UTC).replace(tzinfo=None)
    since_24h = now - timedelta(hours=24)
    open_incidents = (db.scalar(select(func.count(CenterIncident.id)).where(CenterIncident.status == "open")) or 0)
    critical_incidents = (db.scalar(select(func.count(CenterIncident.id)).where(
        CenterIncident.status == "open",
        CenterIncident.severity.in_(["high", "critical"]),
    )) or 0)
    high_risk_exam_events = (db.scalar(select(func.count(ExamMonitoringEvent.id)).where(ExamMonitoringEvent.severity == "high")) or 0)
    critical_exam_events = (db.scalar(select(func.count(ExamMonitoringEvent.id)).where(ExamMonitoringEvent.severity == "critical")) or 0)
    suspicious_devices = (db.scalar(select(func.count(DeviceSession.id)).where(DeviceSession.status == "suspicious")) or 0)
    payment_alerts = _count_payment_alerts(db)
    audit_events_24h = (db.scalar(select(func.count(AuditLog.id)).where(AuditLog.created_at >= since_24h)) or 0)
    last_audit_at = db.scalar(select(func.max(AuditLog.created_at)))

    raw_alerts = [
        _alert("critical_incidents", "Incidents centre critiques ouverts", critical_incidents, "#incidents", warning=1, critical=3),
        _alert("open_incidents", "Incidents centre ouverts", open_incidents, "#incidents", warning=1, critical=10),
        _alert("critical_exam_events", "Evenements examen critiques", critical_exam_events, "#monitoring-examen", warning=1, critical=5),
        _alert("high_risk_exam_events", "Evenements examen a risque eleve", high_risk_exam_events, "#monitoring-examen", warning=3, critical=15),
        _alert("suspicious_devices", "Postes ou appareils suspects", suspicious_devices, "#monitoring-examen", warning=1, critical=5),
        _alert("payment_alerts", "Alertes financieres a traiter", payment_alerts, "#finance", warning=1, critical=10),
        _alert("audit_inactive", "Aucun audit recent sur 24h", 1 if audit_events_24h == 0 else 0, "#audit", warning=1, critical=1),
    ]
    alerts = [alert for alert in raw_alerts if alert is not None]
    critical_alerts = sum(1 for alert in alerts if alert.severity == "critical")
    warning_alerts = sum(1 for alert in alerts if alert.severity == "warning")
    status = "critical" if critical_alerts else "warning" if warning_alerts else "ok"

    return OperationsSummaryRead(
        status=status,
        generated_at=now,
        critical_alerts=critical_alerts,
        warning_alerts=warning_alerts,
        open_incidents=open_incidents,
        critical_incidents=critical_incidents,
        high_risk_exam_events=high_risk_exam_events,
        critical_exam_events=critical_exam_events,
        suspicious_devices=suspicious_devices,
        payment_alerts=payment_alerts,
        audit_events_24h=audit_events_24h,
        last_audit_at=last_audit_at,
        alerts=alerts,
    )


@router.get("/summary", response_model=OperationsSummaryRead)
def operations_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "super_admin")),
) -> OperationsSummaryRead:
    summary = _build_operations_summary(db)
    db.add(
        AuditLog(
            actor_id=current_user.id,
            action="operations.summary_viewed",
            entity="operations",
            entity_id="national-operations",
            details={
                "status": summary.status,
                "critical_alerts": summary.critical_alerts,
                "warning_alerts": summary.warning_alerts,
                "open_incidents": summary.open_incidents,
                "payment_alerts": summary.payment_alerts,
            },
        )
    )
    db.commit()
    return summary
