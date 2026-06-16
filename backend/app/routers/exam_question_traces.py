from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.deps import require_roles
from app.models_exam_attempt import ExamAttempt
from app.models_exam_question_trace import ExamQuestionTrace
from app.models_question import Question
from app.models_user import User

router = APIRouter(prefix="/exam-question-traces", tags=["exam-question-traces"])


class TraceQuestionRead(BaseModel):
    id: str
    category: str
    text: str
    is_active: bool


class ExamQuestionTraceRead(BaseModel):
    id: str
    attempt_id: str
    question_ids: list[str]
    question_count: int
    bank_hash: str
    version_label: str
    selection_mode: str
    created_at: datetime
    questions: list[TraceQuestionRead] = Field(default_factory=list)

    model_config = {"from_attributes": True}


@router.get("/attempts/{attempt_id}", response_model=ExamQuestionTraceRead)
def get_attempt_question_trace(
    attempt_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "super_admin")),
) -> ExamQuestionTraceRead:
    attempt = db.get(ExamAttempt, attempt_id)
    if not attempt:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exam attempt not found")

    trace = db.scalar(select(ExamQuestionTrace).where(ExamQuestionTrace.attempt_id == attempt_id))
    if not trace:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question trace not found")

    questions = []
    if trace.question_ids:
        records = list(db.scalars(select(Question).where(Question.id.in_(trace.question_ids))).all())
        by_id = {question.id: question for question in records}
        questions = [
            TraceQuestionRead(
                id=question.id,
                category=question.category,
                text=question.text,
                is_active=question.is_active,
            )
            for question_id in trace.question_ids
            if (question := by_id.get(question_id))
        ]

    return ExamQuestionTraceRead(
        id=trace.id,
        attempt_id=trace.attempt_id,
        question_ids=trace.question_ids,
        question_count=trace.question_count,
        bank_hash=trace.bank_hash,
        version_label=trace.version_label,
        selection_mode=trace.selection_mode,
        created_at=trace.created_at,
        questions=questions,
    )


@router.get("", response_model=list[ExamQuestionTraceRead])
def list_question_traces(
    attempt_id: str | None = None,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "super_admin")),
) -> list[ExamQuestionTraceRead]:
    query = select(ExamQuestionTrace)
    if attempt_id:
        query = query.where(ExamQuestionTrace.attempt_id == attempt_id)
    query = query.order_by(ExamQuestionTrace.created_at.desc()).limit(max(1, min(limit, 200)))
    traces = list(db.scalars(query).all())
    return [
        ExamQuestionTraceRead(
            id=trace.id,
            attempt_id=trace.attempt_id,
            question_ids=trace.question_ids,
            question_count=trace.question_count,
            bank_hash=trace.bank_hash,
            version_label=trace.version_label,
            selection_mode=trace.selection_mode,
            created_at=trace.created_at,
            questions=[],
        )
        for trace in traces
    ]
