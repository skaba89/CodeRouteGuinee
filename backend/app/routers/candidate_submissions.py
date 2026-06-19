from datetime import datetime
from app.time_utils import utc_now

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

router = APIRouter(prefix="/candidate-submissions", tags=["candidate-submissions"])

STATUSES = {"under_review", "accepted", "rejected", "retake_planned"}


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
def create_submission(payload: SubmissionCreate, db: Session = Depends(get_db)) -> CandidateFollowup:
    candidate = db.get(Candidate, payload.candidate_id)
    if not candidate:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate not found")
    attempt = db.get(ExamAttempt, payload.attempt_id)
    if not attempt:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exam attempt not found")
    if attempt.candidate_id != candidate.id:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Candidate and attempt mismatch")

    item = CandidateFollowup(
        candidate_id=candidate.id,
        attempt_id=attempt.id,
        category=payload.category,
        message=payload.message,
    )
    db.add(item)
    db.flush()
    db.add(
        AuditLog(
            actor_id=None,
            action="candidate_submission.created",
            entity="candidate_submission",
            entity_id=item.id,
            details={"candidate_id": candidate.id, "attempt_id": attempt.id, "category": payload.category},
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
    item = db.get(CandidateFollowup, submission_id)
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Submission not found")
    next_status = _status(payload.status)
    previous_status = item.status
    item.status = next_status
    item.admin_response = payload.admin_response
    item.handled_by_id = current_user.id
    item.handled_at = utc_now()
    db.add(item)
    db.flush()
    db.add(
        AuditLog(
            actor_id=current_user.id,
            action=f"candidate_submission.{next_status}",
            entity="candidate_submission",
            entity_id=item.id,
            details={"candidate_id": item.candidate_id, "attempt_id": item.attempt_id, "previous_status": previous_status, "new_status": next_status},
        )
    )
    db.commit()
    db.refresh(item)
    return item
