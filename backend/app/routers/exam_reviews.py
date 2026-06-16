from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.deps import require_roles
from app.models_audit import AuditLog
from app.models_exam_attempt import ExamAttempt
from app.models_exam_monitoring import ExamMonitoringEvent
from app.models_exam_review import ExamReviewDecision
from app.models_user import User

router = APIRouter(prefix="/exam-reviews", tags=["exam-reviews"])

ALLOWED_DECISIONS = {"clear", "invalidate", "require_retake"}


class ExamReviewDecisionCreate(BaseModel):
    attempt_id: str
    decision: str = Field(min_length=3)
    reason: str = Field(min_length=5)


class ExamReviewDecisionRead(BaseModel):
    id: str
    attempt_id: str
    decision: str
    reason: str
    decided_by_id: str | None = None
    previous_attempt_status: str | None = None
    new_attempt_status: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ExamReviewCaseRead(BaseModel):
    attempt_id: str
    current_status: str
    monitoring_events: int
    monitoring_risk_score: int
    review_status: str
    last_decision: ExamReviewDecisionRead | None = None


def normalize_decision(value: str) -> str:
    decision = value.lower().strip()
    if decision not in ALLOWED_DECISIONS:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid review decision")
    return decision


def apply_decision_to_attempt(attempt: ExamAttempt, decision: str) -> str:
    if decision == "clear":
        return "review_cleared"
    if decision == "invalidate":
        attempt.passed = False
        return "invalidated"
    if decision == "require_retake":
        attempt.passed = False
        return "retake_required"
    return attempt.status


def build_review_status(total_risk_score: int, last_decision: ExamReviewDecision | None) -> str:
    if last_decision:
        return last_decision.decision
    if total_risk_score >= 20:
        return "critical_review_pending"
    if total_risk_score >= 10:
        return "manual_review_pending"
    if total_risk_score >= 4:
        return "watch"
    return "normal"


@router.post("/decisions", response_model=ExamReviewDecisionRead, status_code=status.HTTP_201_CREATED)
def create_review_decision(
    payload: ExamReviewDecisionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "super_admin")),
) -> ExamReviewDecision:
    attempt = db.get(ExamAttempt, payload.attempt_id)
    if not attempt:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exam attempt not found")

    decision = normalize_decision(payload.decision)
    previous_status = attempt.status
    new_status = apply_decision_to_attempt(attempt, decision)
    attempt.status = new_status

    review = ExamReviewDecision(
        attempt_id=attempt.id,
        decision=decision,
        reason=payload.reason,
        decided_by_id=current_user.id,
        previous_attempt_status=previous_status,
        new_attempt_status=new_status,
    )
    db.add(attempt)
    db.add(review)
    db.flush()
    db.add(
        AuditLog(
            actor_id=current_user.id,
            action=f"exam_review.{decision}",
            entity="exam_review_decision",
            entity_id=review.id,
            details={
                "attempt_id": attempt.id,
                "decision": decision,
                "previous_attempt_status": previous_status,
                "new_attempt_status": new_status,
            },
        )
    )
    db.commit()
    db.refresh(review)
    return review


@router.get("/attempts/{attempt_id}", response_model=ExamReviewCaseRead)
def get_review_case(
    attempt_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "super_admin")),
) -> ExamReviewCaseRead:
    attempt = db.get(ExamAttempt, attempt_id)
    if not attempt:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exam attempt not found")

    events = list(db.scalars(select(ExamMonitoringEvent).where(ExamMonitoringEvent.attempt_id == attempt_id)).all())
    total_risk_score = sum(event.risk_score for event in events)
    last_decision = db.scalar(
        select(ExamReviewDecision)
        .where(ExamReviewDecision.attempt_id == attempt_id)
        .order_by(ExamReviewDecision.created_at.desc())
    )
    return ExamReviewCaseRead(
        attempt_id=attempt_id,
        current_status=attempt.status,
        monitoring_events=len(events),
        monitoring_risk_score=total_risk_score,
        review_status=build_review_status(total_risk_score, last_decision),
        last_decision=last_decision,
    )


@router.get("/decisions", response_model=list[ExamReviewDecisionRead])
def list_review_decisions(
    attempt_id: str | None = None,
    decision: str | None = None,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "super_admin")),
) -> list[ExamReviewDecision]:
    query = select(ExamReviewDecision)
    if attempt_id:
        query = query.where(ExamReviewDecision.attempt_id == attempt_id)
    if decision:
        query = query.where(ExamReviewDecision.decision == normalize_decision(decision))
    query = query.order_by(ExamReviewDecision.created_at.desc()).limit(max(1, min(limit, 200)))
    return list(db.scalars(query).all())
