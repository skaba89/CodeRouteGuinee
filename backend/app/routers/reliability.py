from __future__ import annotations

import re
import secrets
from datetime import UTC, datetime, timedelta
from typing import Literal

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.deps import require_roles
from app.models_audit import AuditLog
from app.models_user import User
from app.reliability_config import ReliabilitySettings, get_reliability_settings
from app.reliability_metrics import latest_reliability_evidence, record_reliability_evidence_metric

router = APIRouter(prefix="/operations/reliability", tags=["reliability"])

EvidenceKind = Literal[
    "backup_uploaded",
    "restore_drill_passed",
    "ha_failover_probe_passed",
    "pitr_drill_passed",
]

_ACTIONS: dict[str, str] = {
    "backup_uploaded": "reliability.backup_uploaded",
    "restore_drill_passed": "reliability.restore_drill_passed",
    "ha_failover_probe_passed": "reliability.ha_failover_probe_passed",
    "pitr_drill_passed": "reliability.pitr_drill_passed",
}
_SHA256 = re.compile(r"^[a-f0-9]{64}$")
_MAX_CLOCK_SKEW = timedelta(minutes=5)


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


def _normalized_occurred_at(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)


def _validate_kind_evidence(payload: ReliabilityEvidenceCreate, settings: ReliabilitySettings) -> None:
    if payload.artifact_sha256 is not None and not _SHA256.fullmatch(payload.artifact_sha256):
        raise HTTPException(status_code=422, detail="artifact_sha256 invalide")

    if payload.kind == "backup_uploaded":
        if not payload.artifact_sha256 or not (payload.region or "").strip() or not (payload.reference or "").strip():
            raise HTTPException(status_code=422, detail="preuve backup incomplète")
        region = (payload.region or "").strip().lower()
        target = settings.backup_target_region.strip().lower()
        primary = settings.backup_primary_region.strip().lower()
        if target and region != target:
            raise HTTPException(status_code=422, detail="région backup différente de la cible PRA")
        if settings.backup_require_off_region and primary and region == primary:
            raise HTTPException(status_code=422, detail="preuve backup dans la région primaire refusée")

    elif payload.kind == "restore_drill_passed":
        if not payload.artifact_sha256:
            raise HTTPException(status_code=422, detail="preuve restore sans empreinte du dump")

    elif payload.kind == "ha_failover_probe_passed":
        if payload.availability_percent is None or payload.duration_seconds is None:
            raise HTTPException(status_code=422, detail="preuve failover incomplète")

    elif payload.kind == "pitr_drill_passed":
        if (
            not payload.artifact_sha256
            or not (payload.reference or "").strip()
            or payload.observed_rpo_minutes is None
            or payload.observed_rto_minutes is None
        ):
            raise HTTPException(status_code=422, detail="preuve PITR incomplète")
        if payload.observed_rpo_minutes > settings.dr_rpo_minutes:
            raise HTTPException(
                status_code=422,
                detail=f"RPO PITR observé supérieur à la cible de {settings.dr_rpo_minutes} min",
            )
        if payload.observed_rto_minutes > settings.dr_rto_minutes:
            raise HTTPException(
                status_code=422,
                detail=f"RTO PITR observé supérieur à la cible de {settings.dr_rto_minutes} min",
            )


def _safe_details(payload: ReliabilityEvidenceCreate, *, occurred_at: datetime) -> dict:
    reference = (payload.reference or "").strip()
    if reference and ("://" in reference or "@" in reference):
        raise HTTPException(status_code=422, detail="reference doit être un identifiant interne, pas une URL/credential")
    return {
        "kind": payload.kind,
        "occurred_at": occurred_at.isoformat(),
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
    evidence = latest_reliability_evidence(db)
    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "policy": settings.safe_policy(),
        "last_evidence": {
            kind: (item.get("occurred_at") if isinstance(item, dict) else None)
            for kind, item in evidence.items()
        },
        "last_evidence_details": evidence,
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

    occurred_at = _normalized_occurred_at(payload.occurred_at)
    now = datetime.now(UTC)
    if occurred_at > now + _MAX_CLOCK_SKEW:
        raise HTTPException(status_code=422, detail="occurred_at dépasse la tolérance d'horloge autorisée")

    _validate_kind_evidence(payload, settings)
    details = _safe_details(payload, occurred_at=occurred_at)
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
