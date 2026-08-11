"""Fail-closed candidate update facade.

The legacy generic PATCH accepted an arbitrary string as Candidate.status.
This facade keeps profile edits backward-compatible while reserving `verified`
for the identity-verification workflow and making administrative status changes
explicit and auditable.
"""
from __future__ import annotations

from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.deps import require_roles
from app.models_audit import AuditLog
from app.models_candidate import Candidate
from app.models_user import User
from app.schemas import CandidateRead

router = APIRouter(prefix="/candidates", tags=["candidates"])


class CandidateControlledUpdate(BaseModel):
    first_name: str | None = Field(default=None, min_length=2, max_length=120)
    last_name: str | None = Field(default=None, min_length=2, max_length=120)
    phone: str | None = Field(default=None, min_length=8, max_length=30)
    email: str | None = Field(default=None, max_length=200)
    permit_category: str | None = Field(default=None, pattern=r"^[ABCDE]$")
    city: str | None = None
    date_of_birth: date | None = None
    address: str | None = None

    # `verified` est volontairement absent : seule une décision de contrôle
    # d'identité peut produire cet état. L'import officiel garde son workflow
    # séparé et audité.
    status: Literal["registered", "suspended"] | None = None
    status_reason: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def validate_status_change_reason(self):
        if self.status is not None:
            reason = (self.status_reason or "").strip()
            if len(reason) < 5:
                raise ValueError("status_reason est obligatoire (minimum 5 caractères) pour changer le statut")
        return self


@router.patch("/{candidate_id}", response_model=CandidateRead)
def update_candidate_controlled(
    candidate_id: str,
    payload: CandidateControlledUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "super_admin")),
) -> CandidateRead:
    candidate = db.scalar(
        select(Candidate)
        .where(Candidate.id == candidate_id)
        .with_for_update()
    )
    if not candidate:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidat introuvable")

    before_status = (candidate.status or "registered").strip().lower()
    values = payload.model_dump(exclude_none=True)
    status_reason = str(values.pop("status_reason", "")).strip() or None
    requested_status = values.pop("status", None)
    changed_fields: dict[str, dict[str, object | None]] = {}

    for field, value in values.items():
        if field == "email" and isinstance(value, str):
            value = value.strip().lower()
        elif field in {"first_name", "last_name", "phone", "city", "address"} and isinstance(value, str):
            value = value.strip()
        elif field == "permit_category" and isinstance(value, str):
            value = value.strip().upper()

        old_value = getattr(candidate, field)
        if old_value != value:
            changed_fields[field] = {"from": old_value, "to": value}
            setattr(candidate, field, value)

    if requested_status is not None:
        next_status = str(requested_status).strip().lower()
        if next_status != before_status:
            # Réactiver un dossier suspendu le remet volontairement en
            # `registered`: une ancienne validation d'identité ne doit pas être
            # restaurée silencieusement après une suspension administrative.
            candidate.status = next_status
            changed_fields["status"] = {"from": before_status, "to": next_status}

    if not changed_fields:
        return CandidateRead.model_validate(candidate)

    db.add(candidate)
    db.flush()

    if "status" in changed_fields:
        db.add(
            AuditLog(
                actor_id=current_user.id,
                action="candidate.status_changed",
                entity="candidate",
                entity_id=candidate.id,
                details={
                    "candidate_reference": candidate.reference,
                    "previous_status": before_status,
                    "new_status": candidate.status,
                    "reason": status_reason,
                },
            )
        )

    db.add(
        AuditLog(
            actor_id=current_user.id,
            action="candidate.updated",
            entity="candidate",
            entity_id=candidate.id,
            details={
                "candidate_reference": candidate.reference,
                "changed_fields": sorted(changed_fields.keys()),
                "status_reason": status_reason if "status" in changed_fields else None,
            },
        )
    )
    db.commit()
    db.refresh(candidate)
    return CandidateRead.model_validate(candidate)
