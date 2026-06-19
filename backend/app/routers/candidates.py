from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.deps import require_roles
from app.models_audit import AuditLog
from app.models_candidate import Candidate
from app.models_user import User
from app.schemas import CandidateCreate, CandidateOfficialImportRequest, CandidateOfficialImportResult, CandidateRead

router = APIRouter(prefix="/candidates", tags=["candidates"])


def build_candidate_reference(db: Session) -> str:
    count = db.query(Candidate).count() + 1
    return f"GN-CODE-{datetime.now(UTC).year}-{count:06d}"


@router.get("", response_model=list[CandidateRead])
def list_candidates(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "super_admin", "center")),
) -> list[Candidate]:
    return list(db.scalars(select(Candidate).order_by(Candidate.created_at.desc())).all())


@router.post("", response_model=CandidateRead, status_code=status.HTTP_201_CREATED)
def create_candidate(
    payload: CandidateCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "super_admin")),
) -> Candidate:
    candidate = Candidate(reference=build_candidate_reference(db), **payload.model_dump())
    db.add(candidate)
    db.flush()
    db.add(
        AuditLog(
            actor_id=current_user.id,
            action="candidate.created",
            entity="candidate",
            entity_id=candidate.id,
            details={"reference": candidate.reference, "identity_number": candidate.identity_number},
        )
    )
    db.commit()
    db.refresh(candidate)
    return candidate


@router.post("/import-official", response_model=CandidateOfficialImportResult)
def import_official_candidates(
    payload: CandidateOfficialImportRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "super_admin")),
) -> CandidateOfficialImportResult:
    normalized_identities = [row.identity_number.strip().upper() for row in payload.candidates]
    duplicate_identities = sorted({identity for identity in normalized_identities if normalized_identities.count(identity) > 1})
    if duplicate_identities:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"message": "Duplicate candidate identities in import payload", "identity_numbers": duplicate_identities},
        )

    existing_candidates = {
        candidate.identity_number.upper(): candidate
        for candidate in db.scalars(select(Candidate).where(Candidate.identity_number.in_(normalized_identities))).all()
    }
    if payload.dry_run:
        existing_ids = [identity for identity in normalized_identities if identity in existing_candidates]
        return CandidateOfficialImportResult(
            dry_run=True,
            imported=len(normalized_identities),
            created=len(normalized_identities) - len(existing_ids),
            updated=len(existing_ids),
            skipped=0,
            candidate_ids=[existing_candidates[identity].id for identity in existing_ids],
            references=[existing_candidates[identity].reference for identity in existing_ids],
        )

    created = 0
    updated = 0
    candidate_ids: list[str] = []
    references: list[str] = []

    for row in payload.candidates:
        identity_number = row.identity_number.strip().upper()
        candidate = existing_candidates.get(identity_number)
        if candidate is None:
            candidate = Candidate(reference=build_candidate_reference(db), identity_number=identity_number)
            created += 1
        else:
            updated += 1
        candidate.first_name = row.first_name.strip()
        candidate.last_name = row.last_name.strip()
        candidate.identity_number = identity_number
        candidate.phone = row.phone.strip()
        candidate.permit_category = row.permit_category.strip().upper()
        candidate.status = row.status
        db.add(candidate)
        db.flush()
        candidate_ids.append(candidate.id)
        references.append(candidate.reference)

    db.add(
        AuditLog(
            actor_id=current_user.id,
            action="candidate.official_import",
            entity="candidate",
            entity_id="official-import",
            details={
                "source": payload.source,
                "reason": payload.reason,
                "imported": len(candidate_ids),
                "created": created,
                "updated": updated,
                "references": references[:50],
            },
        )
    )
    db.commit()
    return CandidateOfficialImportResult(
        dry_run=False,
        imported=len(candidate_ids),
        created=created,
        updated=updated,
        skipped=0,
        candidate_ids=candidate_ids,
        references=references,
    )
