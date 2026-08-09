from __future__ import annotations

import re
import secrets
from datetime import UTC, datetime
from typing import Literal

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.deps import require_roles
from app.models_audit import AuditLog
from app.models_user import User
from app.reliability_config import get_reliability_settings
from app.reliability_metrics import record_reliability_evidence_metric

router = APIRouter(prefix="/operations/reliability", tags=["reliability"])

EvidenceKind = Literal[
    "backup_uploaded",
    "restore_drill_passed",
    "ha_failover_probe_passed",
]

_ACTIONS: dict[str, str] = {
    "backup_uploaded": "reliability.backup_uploaded",
    "restore_drill_passed": "reliability.restore_drill_passed",
    "ha_failover_probe_passed": "reliability.ha_failover_probe_passed",
}
_SHA256 = re.compile(r"^[a-f0-9]{64}$")


class ReliabilityEvidenceCreate(BaseModel):
    kind: EvidenceKind
    occurred_at: datetime
    artifact_sha256: str | None = Field(default=None, max_length=64)
    region: str | None = Field(default=None, max_length=80)
    reference: str | None = Field(default=None, max_length=240)
    availability_percent: float | None = Field(default=None, ge=0.0, le=100.0)
    duration_seconds: float | None = Field(default=None, ge=0.0, le=86_400.0)
    observed_rpo_minutes: float | None = Field(default=None, ge=0.0, le=100_000.0)
    observed_rto_minutes: float | None = Field(default=None, ge=0.0, le=100_000.0)


class ReliabilityEvidenceRead(BaseModel):
    accepted: bool
    kind: EvidenceKind
    occurred_at: datetime


def _safe_details(payload: ReliabilityEvidenceCreate) -> dict:
    if payload.artifact_sha256 is not None and not _SHA256.fullmatch(payload.artifact_sha256):
        raise HTTPException(status_code=422, detail="artifact_sha256 invalide")
    reference = (payload.reference or "").strip()
    if reference and ("://" in reference or "@" in reference):
        raise HTTPException(status_code=422, detail="reference doit être un identifiant interne, pas une URL/credential")
    return {
        "kind": payload.kind,
        "occurred_at": payload.occurred_at.isoformat(),
        "artifact_sha256": payload.artifact_sha256,
        "region": (payload.region or "").strip() or None,
        "reference": reference or None,
        "availability_percent": payload.availability_percent,
        "duration_seconds": payload.duration_seconds,
        "observed_rpo_minutes": payload.observed_rpo_minutes,
        "observed_rto_minutes": payload.observed_rto_minutes,
    }


@router.get("")
def reliability_status(
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_roles("admin", "super_admin")),
) -> dict:
    settings = get_reliability_settings()
    last_evidence: dict[str, str | None] = {}
    for kind, action in _ACTIONS.items():
        latest = db.scalar(select(func.max(AuditLog.created_at)).where(AuditLog.action == action))
        last_evidence[kind] = latest.isoformat() if latest else None
    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "policy": settings.safe_policy(),
        "last_evidence": last_evidence,
    }


@router.post("/evidence", response_model=ReliabilityEvidenceRead, status_code=201)
def record_reliability_evidence(
    payload: ReliabilityEvidenceCreate,
    x_reliability_evidence_token: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> ReliabilityEvidenceRead:
    settings = get_reliability_settings()
    if not settings.evidence_enabled:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

    supplied = (x_reliability_evidence_token or "").strip()
    if not supplied or not settings.evidence_token or not secrets.compare_digest(supplied, settings.evidence_token):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Reliability evidence authentication required")

    occurred_at = payload.occurred_at
    if occurred_at.tzinfo is None:
        occurred_at = occurred_at.replace(tzinfo=UTC)
    now = datetime.now(UTC)
    if occurred_at > now.replace(microsecond=0):
        raise HTTPException(status_code=422, detail="occurred_at ne peut pas être dans le futur")

    details = _safe_details(payload)
    db.add(
        AuditLog(
            actor_id=None,
            action=_ACTIONS[payload.kind],
            entity="reliability",
            entity_id=None,
            details=details,
        )
    )
    db.commit()
    record_reliability_evidence_metric(payload.kind, occurred_at)
    return ReliabilityEvidenceRead(accepted=True, kind=payload.kind, occurred_at=occurred_at)
