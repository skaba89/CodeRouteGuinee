from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.deps import require_roles
from app.models_audit import AuditLog
from app.models_candidate import Candidate
from app.models_candidate_followup import CandidateFollowup
from app.models_exam_attempt import ExamAttempt
from app.models_user import User
from app.resource_access import assert_candidate_access

router = APIRouter(prefix="/candidate-submissions", tags=["candidate-submissions"])

STATUSES = {"under_review", "accepted", "rejected", "retake_planned"}
OPEN_STATUSES = {"submitted", "under_review"}
FINAL_STATUSES = {"accepted", "rejected", "retake_planned"}


class SubmissionCreate(BaseModel):
    candidate_id: str
    attempt_id: str
    category: str = "review"
    message: str = Field(min_length=10)


class SubmissionHandle(BaseModel):
    status: str
    admin_response: str = Field(min_length=5)


class SubmissionRead(BaseModel):
    id: str
    candidate_id: str
    attempt_id: str
    category: str
    status: str
    message: str
    admin_response: str | None = None
    handled_by_id: str | None = None
    created_at: datetime
    handled_at: datetime | None = None

    model_config = {"from_attributes": True}


def _status(value: str) -> str:
    value = value.lower().strip()
    if value not in STATUSES:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Status not supported")
    return value


@router.post("", response_model=SubmissionRead, status_code=status.HTTP_201_CREATED)
def create_submission(
    payload: SubmissionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles("candidate", "driving_school", "admin", "super_admin")
    ),
) -> CandidateFollowup:
    candidate = db.get(Candidate, payload.candidate_id)
    if not candidate:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate not found")

    # Le candidat_id est une donnée de requête, jamais une preuve de propriété.
    assert_candidate_access(db, current_user, candidate)

    attempt = db.get(ExamAttempt, payload.attempt_id)
    if not attempt:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exam attempt not found")
    if attempt.candidate_id != candidate.id:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Candidate and attempt mismatch")

    category = payload.category.strip().lower() or "review"
    existing_open = db.scalar(
        select(CandidateFollowup.id)
        .where(
            CandidateFollowup.candidate_id == candidate.id,
            CandidateFollowup.attempt_id == attempt.id,
            CandidateFollowup.category == category,
            CandidateFollowup.status.in_(OPEN_STATUSES),
        )
        .limit(1)
    )
    if existing_open:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "CANDIDATE_SUBMISSION_ALREADY_OPEN",
                "message": "Un recours de cette catégorie est déjà en cours de traitement pour cette tentative.",
            },
        )

    item = CandidateFollowup(
        candidate_id=candidate.id,
        attempt_id=attempt.id,
        category=category,
        message=payload.message.strip(),
    )
    db.add(item)
    db.flush()
    db.add(
        AuditLog(
            actor_id=current_user.id,
            action="candidate_submission.created",
            entity="candidate_submission",
            entity_id=item.id,
            details={
                "candidate_id": candidate.id,
                "attempt_id": attempt.id,
                "category": category,
                "submitted_by_role": current_user.role,
            },
        )
    )
    db.commit()
    db.refresh(item)
    return item


@router.get("", response_model=list[SubmissionRead])
def list_submissions(
    candidate_id: str | None = None,
    attempt_id: str | None = None,
    status_filter: str | None = None,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "super_admin")),
) -> list[CandidateFollowup]:
    query = select(CandidateFollowup)
    if candidate_id:
        query = query.where(CandidateFollowup.candidate_id == candidate_id)
    if attempt_id:
        query = query.where(CandidateFollowup.attempt_id == attempt_id)
    if status_filter:
        query = query.where(CandidateFollowup.status == status_filter)
    query = query.order_by(CandidateFollowup.created_at.desc()).limit(max(1, min(limit, 200)))
    return list(db.scalars(query).all())


@router.post("/{submission_id}/handle", response_model=SubmissionRead)
def handle_submission(
    submission_id: str,
    payload: SubmissionHandle,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "super_admin")),
) -> CandidateFollowup:
    item = db.scalar(
        select(CandidateFollowup)
        .where(CandidateFollowup.id == submission_id)
        .with_for_update()
    )
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Submission not found")
    next_status = _status(payload.status)
    previous_status = item.status

    # Les décisions finales sont stables. Une réouverture devra passer par un
    # workflow explicite plutôt que par une mutation silencieuse du même dossier.
    if previous_status in FINAL_STATUSES:
        if previous_status == next_status:
            return item
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "CANDIDATE_SUBMISSION_ALREADY_FINAL",
                "message": "Ce recours a déjà reçu une décision finale.",
                "current_status": previous_status,
            },
        )

    item.status = next_status
    item.admin_response = payload.admin_response.strip()
    item.handled_by_id = current_user.id
    item.handled_at = datetime.now(UTC).replace(tzinfo=None)
    db.add(item)
    db.flush()
    db.add(
        AuditLog(
            actor_id=current_user.id,
            action=f"candidate_submission.{next_status}",
            entity="candidate_submission",
            entity_id=item.id,
            details={
                "candidate_id": item.candidate_id,
                "attempt_id": item.attempt_id,
                "previous_status": previous_status,
                "new_status": next_status,
            },
        )
    )
    db.commit()
    db.refresh(item)
    return item
