"""Métriques P10.2 à faible cardinalité et sans PII.

Les labels HTTP utilisent le template FastAPI/Starlette (`/exams/{id}`), jamais
l'URL brute. Aucun candidat, attempt_id, email ou valeur de réponse n'est
exporté vers Prometheus.
"""
from __future__ import annotations

import os
import time
from datetime import UTC, datetime

from prometheus_client import CollectorRegistry, Counter, Gauge, Histogram, generate_latest, multiprocess
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from starlette.middleware.base import BaseHTTPMiddleware

from app.models_audit import AuditLog

HTTP_REQUESTS = Counter(
    "coderoute_http_requests_total",
    "Nombre de requêtes HTTP traitées.",
    ("method", "route", "status_class"),
)
HTTP_DURATION = Histogram(
    "coderoute_http_request_duration_seconds",
    "Durée des requêtes HTTP.",
    ("method", "route"),
    buckets=(0.05, 0.1, 0.25, 0.5, 0.75, 1.0, 1.5, 2.5, 5.0, 10.0),
)
HTTP_INFLIGHT = Gauge(
    "coderoute_http_inflight_requests",
    "Nombre de requêtes HTTP actuellement en cours.",
    multiprocess_mode="livesum",
)
READINESS_COMPONENT = Gauge(
    "coderoute_readiness_component_state",
    "État d'un composant de readiness: 1=ok/disabled, 0.5=warning/degraded, 0=error.",
    ("component",),
    multiprocess_mode="livemin",
)
RELIABILITY_EVIDENCE_LAST_SUCCESS = Gauge(
    "coderoute_reliability_evidence_last_success_timestamp_seconds",
    "Dernier événement d'exploitation réussi par type.",
    ("kind",),
    multiprocess_mode="livemax",
)

_EVIDENCE_ACTIONS = {
    "backup_uploaded": "reliability.backup_uploaded",
    "restore_drill_passed": "reliability.restore_drill_passed",
    "ha_failover_probe_passed": "reliability.ha_failover_probe_passed",
}


def _route_template(request) -> str:
    route = request.scope.get("route")
    template = getattr(route, "path", None)
    if not template or not isinstance(template, str):
        return "unmatched"
    return template[:160]


class ReliabilityMetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        if request.url.path == "/internal/metrics":
            return await call_next(request)

        method = request.method.upper()[:12]
        started = time.perf_counter()
        status_code = 500
        HTTP_INFLIGHT.inc()
        try:
            response = await call_next(request)
            status_code = int(response.status_code)
            return response
        finally:
            elapsed = max(0.0, time.perf_counter() - started)
            route = _route_template(request)
            status_class = f"{max(1, min(5, status_code // 100))}xx"
            HTTP_REQUESTS.labels(method=method, route=route, status_class=status_class).inc()
            HTTP_DURATION.labels(method=method, route=route).observe(elapsed)
            HTTP_INFLIGHT.dec()


def update_readiness_metrics(checks: dict[str, dict]) -> None:
    mapping = {
        "ok": 1.0,
        "disabled": 1.0,
        "warning": 0.5,
        "degraded": 0.5,
        "unknown": 0.0,
        "error": 0.0,
    }
    for component, check in checks.items():
        state = str(check.get("status", "unknown")).lower()
        READINESS_COMPONENT.labels(component=component).set(mapping.get(state, 0.0))


def refresh_reliability_evidence_metrics(db: Session) -> None:
    """Recharge les timestamps depuis le journal central après un restart API."""
    for kind, action in _EVIDENCE_ACTIONS.items():
        latest = db.scalar(select(func.max(AuditLog.created_at)).where(AuditLog.action == action))
        timestamp = 0.0
        if latest is not None:
            if latest.tzinfo is None:
                latest = latest.replace(tzinfo=UTC)
            timestamp = latest.timestamp()
        RELIABILITY_EVIDENCE_LAST_SUCCESS.labels(kind=kind).set(timestamp)


def record_reliability_evidence_metric(kind: str, occurred_at: datetime) -> None:
    if kind not in _EVIDENCE_ACTIONS:
        return
    value = occurred_at
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    RELIABILITY_EVIDENCE_LAST_SUCCESS.labels(kind=kind).set(value.timestamp())


def prometheus_payload() -> bytes:
    if os.getenv("PROMETHEUS_MULTIPROC_DIR"):
        registry = CollectorRegistry(support_collectors_without_names=True)
        multiprocess.MultiProcessCollector(registry)
        return generate_latest(registry)
    return generate_latest()
