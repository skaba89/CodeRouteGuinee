from __future__ import annotations

import secrets

from fastapi import APIRouter, HTTPException, Request, Response, status
from prometheus_client import CONTENT_TYPE_LATEST

from app.db.session import SessionLocal
from app.reliability_config import get_reliability_settings
from app.reliability_metrics import prometheus_payload, refresh_reliability_evidence_metrics

router = APIRouter(tags=["metrics"])


def _provided_token(request: Request) -> str:
    authorization = request.headers.get("authorization", "").strip()
    if authorization.lower().startswith("bearer "):
        return authorization[7:].strip()
    return request.headers.get("x-metrics-token", "").strip()


@router.get("/internal/metrics", include_in_schema=False)
def metrics(request: Request) -> Response:
    settings = get_reliability_settings()
    if not settings.metrics_enabled:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

    supplied = _provided_token(request)
    if not supplied or not settings.metrics_token or not secrets.compare_digest(supplied, settings.metrics_token):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Metrics authentication required")

    try:
        db = SessionLocal()
        try:
            refresh_reliability_evidence_metrics(db)
        finally:
            db.close()
    except Exception:
        pass

    return Response(
        content=prometheus_payload(),
        headers={"Content-Type": CONTENT_TYPE_LATEST, "Cache-Control": "no-store"},
    )
