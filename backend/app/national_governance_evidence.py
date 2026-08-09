"""Integrity boundary for P12 institutional homologation evidence.

External documents remain in the institution's GED/evidence vault. CodeRoute stores
only a stable internal reference, the document SHA-256 and traceability metadata.
This module deliberately does not fetch remote documents or claim their legal
validity; it only prevents a dossier from progressing with un-hashed references.
"""
from __future__ import annotations

import re
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import HTTPException
from pydantic import BaseModel, Field, model_validator
from sqlalchemy.orm import Session

from app.models_user import User
from app.national_governance import (
    MANDATORY_EVIDENCE,
    _audit,
    _dossier_record,
    _dump,
    _load,
    _naive,
    _now,
    _serialize,
)

_SHA256_RE = re.compile(r"^[a-f0-9]{64}$")
_MAX_CLOCK_SKEW = timedelta(minutes=5)


class EvidenceIntegrityRequest(BaseModel):
    code: str = Field(min_length=3, max_length=80)
    reference: str = Field(min_length=3, max_length=255)
    artifact_sha256: str = Field(min_length=64, max_length=64)
    issued_at: datetime
    note: str | None = Field(default=None, max_length=1500)

    @model_validator(mode="after")
    def normalize_and_validate(self):
        self.code = self.code.strip().lower()
        self.reference = self.reference.strip()
        self.artifact_sha256 = self.artifact_sha256.strip().lower()

        if self.code not in MANDATORY_EVIDENCE:
            raise ValueError(f"code de preuve inconnu: {self.code}")
        if not _SHA256_RE.fullmatch(self.artifact_sha256):
            raise ValueError("artifact_sha256 doit contenir exactement 64 caractères hexadécimaux")
        if "://" in self.reference or "@" in self.reference:
            raise ValueError("reference doit être un identifiant GED interne, pas une URL/credential")
        if any(ord(char) < 32 for char in self.reference):
            raise ValueError("reference contient un caractère de contrôle")
        return self


def _utc(value: datetime) -> datetime:
    return value.astimezone(UTC) if value.tzinfo is not None else value.replace(tzinfo=UTC)


def _validate_issued_at(value: datetime, *, now: datetime | None = None) -> datetime:
    issued_at = _utc(value)
    current = now or _now()
    if issued_at > current + _MAX_CLOCK_SKEW:
        raise HTTPException(status_code=422, detail="issued_at dépasse la tolérance d'horloge autorisée")
    return issued_at


def _entry_is_integral(entry: Any, *, now: datetime | None = None) -> tuple[bool, str | None]:
    if not isinstance(entry, dict):
        return False, "entry_not_object"
    reference = str(entry.get("reference") or "").strip()
    digest = str(entry.get("artifact_sha256") or "").strip().lower()
    issued_raw = entry.get("issued_at")
    if not reference or "://" in reference or "@" in reference:
        return False, "reference_invalid"
    if not _SHA256_RE.fullmatch(digest):
        return False, "sha256_invalid"
    if not isinstance(issued_raw, str) or not issued_raw.strip():
        return False, "issued_at_missing"
    try:
        issued_at = datetime.fromisoformat(issued_raw.replace("Z", "+00:00"))
    except ValueError:
        return False, "issued_at_invalid"
    try:
        _validate_issued_at(issued_at, now=now)
    except HTTPException:
        return False, "issued_at_future"
    return True, None


def attach_hashed_evidence(
    db: Session,
    actor: User,
    reference: str,
    payload: EvidenceIntegrityRequest,
) -> dict:
    record, document = _dossier_record(db, reference)
    if record.status not in {"draft", "evidence_review"}:
        raise HTTPException(status_code=409, detail="Le dossier n'accepte plus de nouvelles preuves")

    issued_at = _validate_issued_at(payload.issued_at)
    evidence = dict(document.get("evidence") or {})
    history = list(document.get("evidence_history") or [])
    previous = evidence.get(payload.code)
    if isinstance(previous, dict):
        history.append(
            {
                "code": payload.code,
                "reference": previous.get("reference"),
                "artifact_sha256": previous.get("artifact_sha256"),
                "issued_at": previous.get("issued_at"),
                "replaced_by": actor.id,
                "replaced_at": _now().isoformat(),
            }
        )

    evidence[payload.code] = {
        "reference": payload.reference,
        "artifact_sha256": payload.artifact_sha256,
        "issued_at": issued_at.isoformat(),
        "note": payload.note,
        "attached_by": actor.id,
        "attached_at": _now().isoformat(),
    }
    document["evidence"] = evidence
    document["evidence_history"] = history
    record.status = "evidence_review"
    record.updated_at = _naive()
    record.scope = _dump(document)
    _audit(
        db,
        actor,
        "governance.homologation_evidence_attached",
        reference,
        {
            "evidence_code": payload.code,
            "artifact_sha256": payload.artifact_sha256,
            "evidence_reference": payload.reference,
            "replacement": isinstance(previous, dict),
        },
    )
    db.commit()
    return _serialize(record, _load(record))


def validate_dossier_evidence_integrity(
    db: Session,
    reference: str,
    *,
    now: datetime | None = None,
) -> dict:
    _record, document = _dossier_record(db, reference)
    evidence = document.get("evidence") if isinstance(document.get("evidence"), dict) else {}
    missing = sorted(MANDATORY_EVIDENCE - set(evidence.keys()))
    if missing:
        raise HTTPException(
            status_code=409,
            detail={"code": "HOMOLOGATION_EVIDENCE_MISSING", "missing": missing},
        )

    invalid: list[dict[str, str]] = []
    for code in sorted(MANDATORY_EVIDENCE):
        valid, reason = _entry_is_integral(evidence.get(code), now=now)
        if not valid:
            invalid.append({"code": code, "reason": reason or "invalid"})
    if invalid:
        raise HTTPException(
            status_code=409,
            detail={"code": "HOMOLOGATION_EVIDENCE_INTEGRITY_INVALID", "invalid": invalid},
        )

    return {
        "valid": True,
        "required_count": len(MANDATORY_EVIDENCE),
        "evidence_count": len(MANDATORY_EVIDENCE),
        "hashes": {code: str(evidence[code]["artifact_sha256"]).lower() for code in sorted(MANDATORY_EVIDENCE)},
    }
