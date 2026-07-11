from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.deps import require_roles
from app.models_audit import AuditLog
from app.models_question import Question
from app.models_question_governance import QuestionGovernanceDecision
from app.models_user import User
from app.schemas import QuestionGovernanceDecisionCreate, QuestionGovernanceRead

router = APIRouter(prefix="/question-governance", tags=["question-governance"])


def _latest_decision_by_question(db: Session, question_ids: list[str]) -> dict[str, QuestionGovernanceDecision]:
    decisions = db.scalars(
        select(QuestionGovernanceDecision)
        .where(QuestionGovernanceDecision.question_id.in_(question_ids))
        .order_by(QuestionGovernanceDecision.created_at.desc())
    ).all()
    latest: dict[str, QuestionGovernanceDecision] = {}
    for decision in decisions:
        latest.setdefault(decision.question_id, decision)
    return latest


def _read_model(question: Question, decision: QuestionGovernanceDecision | None = None) -> QuestionGovernanceRead:
    latest_status = decision.status if decision else ("published" if question.is_active else "suspended")
    return QuestionGovernanceRead(
        question_id=question.id,
        category=question.category,
        text=question.text,
        is_active=question.is_active,
        latest_status=latest_status,
        latest_reason=decision.reason if decision else None,
        decided_by_id=decision.decided_by_id if decision else None,
        decided_at=decision.created_at if decision else None,
    )


@router.get("", response_model=list[QuestionGovernanceRead])
def list_question_governance(
    category: str | None = None,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "super_admin")),
) -> list[QuestionGovernanceRead]:
    query = select(Question)
    if category:
        query = query.where(Question.category == category)
    questions = list(db.scalars(query.order_by(Question.created_at.desc()).limit(max(1, min(limit, 200)))).all())
    latest = _latest_decision_by_question(db, [question.id for question in questions]) if questions else {}
    return [_read_model(question, latest.get(question.id)) for question in questions]


@router.post("/{question_id}/decision", response_model=QuestionGovernanceRead)
def decide_question_governance(
    question_id: str,
    payload: QuestionGovernanceDecisionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "super_admin")),
) -> QuestionGovernanceRead:
    question = db.get(Question, question_id)
    if not question:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found")

    previous_active = question.is_active
    question.is_active = payload.status == "published"

    # Synchroniser le statut de validation officiel (certification DNTT) :
    # une décision de gouvernance met à jour le workflow certifiant pour que
    # les deux systèmes restent cohérents. Une question "published" devient
    # éligible au tirage de l'examen réel.
    from datetime import UTC, datetime
    if payload.status == "published":
        question.validation_status = "approved"
        question.validated_by = current_user.id
        question.validated_at = datetime.now(UTC).replace(tzinfo=None)
        question.rejection_reason = None
    elif payload.status in ("needs_revision", "rejected"):
        question.validation_status = "rejected"
        question.rejection_reason = payload.reason
        question.validated_by = current_user.id
    elif payload.status == "suspended":
        question.validation_status = "draft"

    decision = QuestionGovernanceDecision(
        question_id=question.id,
        status=payload.status,
        reason=payload.reason,
        decided_by_id=current_user.id,
    )
    db.add(question)
    db.add(decision)
    db.flush()
    db.add(
        AuditLog(
            actor_id=current_user.id,
            action=f"question_governance.{payload.status}",
            entity="question",
            entity_id=question.id,
            details={
                "category": question.category,
                "previous_active": previous_active,
                "new_active": question.is_active,
                "reason": payload.reason,
            },
        )
    )
    db.commit()
    db.refresh(question)
    db.refresh(decision)
    return _read_model(question, decision)
