from app.time_utils import utc_now

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.deps import require_roles
from app.models_audit import AuditLog
from app.models_candidate import Candidate
from app.models_candidate_identity import CandidateIdentityCheck
from app.models_user import User
from app.schemas import CandidateIdentityCreate, CandidateIdentityDecision, CandidateIdentityRead

router = APIRouter(prefix="/candidate-identity", tags=["candidate-identity"])


@router.post("", response_model=CandidateIdentityRead, status_code=status.HTTP_201_CREATED)
def create_identity_check(payload: CandidateIdentityCreate, db: Session = Depends(get_db)) -> CandidateIdentityCheck:
    candidate = db.get(Candidate, payload.candidate_id)
    if not candidate:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate not found")

    item = CandidateIdentityCheck(**payload.model_dump(), status="pending")
    db.add(item)
    db.flush()
    db.add(
        AuditLog(
            actor_id=None,
            action="candidate_identity.submitted",
            entity="candidate_identity",
            entity_id=item.id,
            details={
                "candidate_id": candidate.id,
                "candidate_reference": candidate.reference,
                "document_type": item.document_type,
            },
        )
    )
    db.commit()
    db.refresh(item)
    return item


@router.get("", response_model=list[CandidateIdentityRead])
def list_identity_checks(
    status_filter: str | None = None,
    candidate_id: str | None = None,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "super_admin")),
) -> list[CandidateIdentityCheck]:
    query = select(CandidateIdentityCheck)
    if status_filter:
        query = query.where(CandidateIdentityCheck.status == status_filter)
    if candidate_id:
        query = query.where(CandidateIdentityCheck.candidate_id == candidate_id)
    query = query.order_by(CandidateIdentityCheck.created_at.desc()).limit(max(1, min(limit, 200)))
    return list(db.scalars(query).all())


@router.post("/{check_id}/decision", response_model=CandidateIdentityRead)
def decide_identity_check(
    check_id: str,
    payload: CandidateIdentityDecision,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "super_admin")),
) -> CandidateIdentityCheck:
    item = db.get(CandidateIdentityCheck, check_id)
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Identity check not found")

    previous_status = item.status
    item.status = payload.status
    item.verified_by_id = current_user.id
    item.decision_reason = payload.reason
    item.decided_at = utc_now()
    db.add(item)
    db.flush()
    db.add(
        AuditLog(
            actor_id=current_user.id,
            action=f"candidate_identity.{payload.status}",
            entity="candidate_identity",
            entity_id=item.id,
            details={
                "candidate_id": item.candidate_id,
                "document_type": item.document_type,
                "previous_status": previous_status,
                "new_status": payload.status,
            },
        )
    )
    db.commit()
    db.refresh(item)
    return item
