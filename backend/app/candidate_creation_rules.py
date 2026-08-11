from __future__ import annotations

from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select, text
from sqlalchemy.orm import Session

from app.models_candidate import Candidate

_CANDIDATE_REFERENCE_LOCK_ID = 2026081104


def acquire_candidate_reference_lock(db: Session) -> None:
    """Sérialise les invariants de création candidat sur PostgreSQL."""
    if db.get_bind().dialect.name == "postgresql":
        db.execute(
            text("SELECT pg_advisory_xact_lock(:lock_id)"),
            {"lock_id": _CANDIDATE_REFERENCE_LOCK_ID},
        )


def build_candidate_reference_locked(db: Session) -> str:
    acquire_candidate_reference_lock(db)
    count = (db.scalar(select(func.count(Candidate.id))) or 0) + 1
    return f"GN-CODE-{datetime.now(UTC).year}-{count:06d}"


def assert_candidate_identity_phone_unique(db: Session, identity_number: str, phone: str) -> None:
    # Le contrôle de doublon et l'allocation GN-CODE partagent le même verrou.
    # Deux inscriptions simultanées avec la même identité ne peuvent donc pas
    # franchir toutes les deux la lecture "aucun doublon" avant insertion.
    acquire_candidate_reference_lock(db)
    normalized_identity = (identity_number or "").strip().upper()
    normalized_phone = (phone or "").strip()
    duplicate = db.scalar(
        select(Candidate.id).where(
            or_(
                func.upper(Candidate.identity_number) == normalized_identity,
                Candidate.phone == normalized_phone,
            )
        )
    )
    if duplicate:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Un candidat existe déjà avec ce numéro d'identité ou ce téléphone.",
        )
