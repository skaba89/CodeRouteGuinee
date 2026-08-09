from __future__ import annotations

import secrets
import time

from fastapi import APIRouter, HTTPException, Request, Response, status
from prometheus_client import CONTENT_TYPE_LATEST

from app.audit_chain import verify_audit_chain
from app.db.session import SessionLocal
from app.reliability_config import get_reliability_settings
from app.reliability_metrics import prometheus_payload, refresh_reliability_evidence_metrics
from app.soc_config import get_soc_settings
from app.soc_metrics import record_audit_chain_check, record_soc_policy_state

router = APIRouter(tags=["metrics"])
_AUDIT_VERIFY_LAST_MONOTONIC = 0.0


def _provided_token(request: Request) -> str:
    authorization = request.headers.get("authorization", "").strip()
    if authorization.lower().startswith("bearer "):
        return authorization[7:].strip()
    return request.headers.get("x-metrics-token", "").strip()


def _maybe_refresh_audit_integrity(db) -> None:
    global _AUDIT_VERIFY_LAST_MONOTONIC
    soc = get_soc_settings()
    if not soc.enabled or not soc.audit_chain_enabled:
        return
    now = time.monotonic()
    if now - _AUDIT_VERIFY_LAST_MONOTONIC < soc.audit_verify_interval_seconds:
        return
    report = verify_audit_chain(db)
    record_audit_chain_check(bool(report.get("valid", False)))
    _AUDIT_VERIFY_LAST_MONOTONIC = now


@router.get("/internal/metrics", include_in_schema=False)
def metrics(request: Request) -> Response:
    settings = get_reliability_settings()
    if not settings.metrics_enabled:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

    supplied = _provided_token(request)
    if not supplied or not settings.metrics_token or not secrets.compare_digest(supplied, settings.metrics_token):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Metrics authentication required")

    soc = get_soc_settings()
    record_soc_policy_state(enabled=soc.enabled, audit_chain_enabled=soc.audit_chain_enabled)

    try:
        db = SessionLocal()
        try:
            refresh_reliability_evidence_metrics(db)
            _maybe_refresh_audit_integrity(db)
        finally:
            db.close()
    except Exception:
        # Le scrape reste disponible même si PostgreSQL est temporairement indisponible.
        # L'alerte de fraîcheur du contrôle d'audit signalera l'absence de vérification.
        pass

    return Response(
        content=prometheus_payload(),
        headers={"Content-Type": CONTENT_TYPE_LATEST, "Cache-Control": "no-store"},
    )
