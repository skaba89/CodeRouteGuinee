"""Garde P12 temporaire tant que le moteur officiel est mono-politique.

Le moteur actuel expose un seul contrat Catégorie B. Autoriser simultanément
deux codes de politique actifs rendrait `active_policy()` ambigu et pourrait
faire croire qu'une Catégorie A/C/D est réellement supportée. Ce garde doit être
retiré uniquement quand le runtime devient explicitement multi-politique.
"""
from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models_institutional_authorization import InstitutionalAuthorization
from app.national_governance import POLICY_KIND, _load, _policy_record


def assert_single_active_policy_code(db: Session, reference: str) -> None:
    _record, candidate = _policy_record(db, reference)
    candidate_code = str(candidate.get("code", "")).strip()

    active_records = db.scalars(
        select(InstitutionalAuthorization).where(
            InstitutionalAuthorization.status == "active",
            InstitutionalAuthorization.reference.like("DNTT-POLICY-%"),
        )
    ).all()
    for record in active_records:
        if record.reference == reference:
            continue
        document = _load(record)
        if document.get("kind") != POLICY_KIND:
            continue
        active_code = str(document.get("code", "")).strip()
        if active_code and active_code != candidate_code:
            raise HTTPException(
                status_code=409,
                detail={
                    "code": "ACTIVE_POLICY_CODE_CONFLICT",
                    "message": "Le moteur officiel courant n'accepte qu'un seul code de politique nationale actif.",
                    "active_reference": record.reference,
                    "active_code": active_code,
                    "candidate_reference": reference,
                    "candidate_code": candidate_code,
                },
            )
