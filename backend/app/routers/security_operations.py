from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

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
from app.soc_config import SOCSettings, get_soc_settings
from app.soc_metrics import record_audit_chain_check

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


def build_security_go_live_controls(
    soc: SOCSettings,
    audit: dict[str, Any],
    alerts: list[dict],
) -> dict:
    """Return fail-closed P11 go-live controls without mutating infrastructure.

    These checks intentionally require the operational flags to be enabled only
    after the external WAF/SIEM/OTLP components have been proven by operators.
    A green result is therefore a runtime configuration gate, not proof that the
    external providers actually delivered the expected service.
    """
    controls = [
        {
            "code": "soc_enabled",
            "passed": soc.enabled,
            "detail": "SOC_ENABLED=true" if soc.enabled else "SOC encore dormant",
        },
        {
            "code": "audit_hmac_enabled",
            "passed": soc.audit_chain_enabled,
            "detail": "chaîne HMAC active" if soc.audit_chain_enabled else "AUDIT_CHAIN_ENABLED=false",
        },
        {
            "code": "audit_chain_valid",
            "passed": bool(soc.audit_chain_enabled and audit.get("valid") is True),
            "detail": "chaîne audit valide" if audit.get("valid") is True else "chaîne audit non validée",
        },
        {
            "code": "otel_enabled",
            "passed": bool(soc.otel_traces_enabled and soc.otel_endpoint),
            "detail": "OTLP actif avec endpoint configuré" if soc.otel_traces_enabled and soc.otel_endpoint else "OTLP non activé/configuré",
        },
        {
            "code": "waf_enforced",
            "passed": bool(soc.waf_required and soc.waf_provider),
            "detail": f"WAF requis via {soc.waf_provider}" if soc.waf_required and soc.waf_provider else "WAF_REQUIRED/provider non finalisé",
        },
        {
            "code": "siem_enforced",
            "passed": bool(soc.siem_required),
            "detail": "SIEM_REQUIRED=true" if soc.siem_required else "SIEM_REQUIRED=false",
        },
        {
            "code": "no_active_security_alert",
            "passed": not alerts,
            "detail": "aucun signal sécurité actif" if not alerts else f"{len(alerts)} signal(aux) sécurité actif(s)",
        },
    ]
    blockers = [item["code"] for item in controls if not item["passed"]]
    return {
        "ready": not blockers,
        "controls": controls,
        "blockers": blockers,
        "external_evidence_still_required": [
            "preuve d'ingestion SIEM/log drain et rétention/RBAC",
            "preuve collector OTLP privé et absence de PII dans les traces",
            "preuve WAF/DDoS et origine non contournable",
            "tests staging confidentialité/alerting/charge/chaos",
            "sign-off technique, exploitation, sécurité et autorité métier",
        ],
    }


@router.get("/status")
def security_status(
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_roles("admin", "super_admin")),
) -> dict:
    now = datetime.now(UTC)
    soc = get_soc_settings()
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
    if soc.enabled and soc.audit_chain_enabled:
        record_audit_chain_check(bool(audit.get("valid", False)), now)

    alerts: list[dict] = []
    if soc.enabled and not soc.audit_chain_enabled:
        alerts.append({"code": "AUDIT_CHAIN_DISABLED", "severity": "critical"})
    elif soc.enabled and soc.audit_chain_enabled and not audit.get("valid", False):
        alerts.append({"code": "AUDIT_CHAIN_INVALID", "severity": "critical"})
    if login_blocked_15m > 0 or login_failed_15m >= 10:
        alerts.append({"code": "AUTH_BRUTE_FORCE_SIGNAL", "severity": "warning"})
    if suspicious_devices > 0:
        alerts.append({"code": "SUSPICIOUS_DEVICE", "severity": "warning"})
    if critical_incidents > 0:
        alerts.append({"code": "CRITICAL_CENTER_INCIDENT", "severity": "critical"})

    critical = any(item["severity"] == "critical" for item in alerts)
    warning = any(item["severity"] == "warning" for item in alerts)
    status_value = "disabled" if not soc.enabled else "critical" if critical else "warning" if warning else "ok"
    go_live = build_security_go_live_controls(soc, audit, alerts)

    return {
        "status": status_value,
        "generated_at": now.isoformat(),
        "soc_policy": soc.safe_policy(),
        "audit_chain": audit,
        "go_live": go_live,
        "signals": {
            "login_failed_15m": login_failed_15m,
            "login_blocked_15m": login_blocked_15m,
            "login_failed_24h": login_failed_24h,
            "suspicious_devices": suspicious_devices,
            "critical_center_incidents": critical_incidents,
        },
        "alerts": alerts,
    }
