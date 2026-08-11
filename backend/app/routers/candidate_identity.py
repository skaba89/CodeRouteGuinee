from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.deps import require_roles
from app.models_audit import AuditLog
from app.models_candidate import Candidate
from app.models_candidate_identity import CandidateIdentityCheck
from app.models_user import User
from app.resource_access import assert_candidate_access
from app.schemas import CandidateIdentityCreate, CandidateIdentityDecision, CandidateIdentityRead

router = APIRouter(prefix="/candidate-identity", tags=["candidate-identity"])


@router.post("", response_model=CandidateIdentityRead, status_code=status.HTTP_201_CREATED)
def create_identity_check(
    payload: CandidateIdentityCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles("candidate", "driving_school", "admin", "super_admin", "center")
    ),
) -> CandidateIdentityCheck:
    candidate = db.get(Candidate, payload.candidate_id)
    if not candidate:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate not found")

    # Un ID candidat fourni par le frontend ne constitue jamais une autorisation.
    # Candidat, auto-école et centre doivent être réellement rattachés au dossier.
    assert_candidate_access(db, current_user, candidate)

    pending = db.scalar(
        select(CandidateIdentityCheck.id)
        .where(
            CandidateIdentityCheck.candidate_id == candidate.id,
            CandidateIdentityCheck.status == "pending",
        )
        .limit(1)
    )
    if pending:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "IDENTITY_CHECK_ALREADY_PENDING",
                "message": "Une vérification d'identité est déjà en attente pour ce candidat.",
            },
        )

    item = CandidateIdentityCheck(**payload.model_dump(), status="pending")
    db.add(item)
    db.flush()
    db.add(
        AuditLog(
            actor_id=current_user.id,
            action="candidate_identity.submitted",
            entity="candidate_identity",
            entity_id=item.id,
            details={
                "candidate_id": candidate.id,
                "candidate_reference": candidate.reference,
                "document_type": item.document_type,
                "submitted_by_role": current_user.role,
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
    # Verrou de ligne : deux décisions administratives simultanées ne peuvent
    # pas laisser Candidate.status et CandidateIdentityCheck.status divergents.
    item = db.scalar(
        select(CandidateIdentityCheck)
        .where(CandidateIdentityCheck.id == check_id)
        .with_for_update()
    )
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Identity check not found")

    candidate = db.get(Candidate, item.candidate_id)
    if not candidate:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "IDENTITY_CANDIDATE_MISSING",
                "message": "Le dossier candidat lié à cette vérification est introuvable.",
            },
        )

    previous_status = item.status
    previous_candidate_status = candidate.status
    item.status = payload.status
    item.verified_by_id = current_user.id
    item.decision_reason = payload.reason
    item.decided_at = datetime.now(UTC).replace(tzinfo=None)

    # `suspended` reste une décision administrative supérieure : une validation
    # documentaire ne réactive jamais silencieusement un candidat suspendu.
    if payload.status == "verified" and candidate.status != "suspended":
        candidate.status = "verified"
    elif payload.status in {"rejected", "needs_review"} and candidate.status == "verified":
        candidate.status = "registered"

    db.add(item)
    db.add(candidate)
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
                "previous_candidate_status": previous_candidate_status,
                "new_candidate_status": candidate.status,
            },
        )
    )
    db.commit()
    db.refresh(item)
    return item
