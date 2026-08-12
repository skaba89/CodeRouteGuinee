"""Media-aware candidate exam question delivery.

This route preserves the public exam questions contract while resolving the
normalized QuestionMedia -> MediaAsset association used by the media library.
Legacy Question.media_* fields remain available through resolve_exam_media as a
migration fallback.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.deps import require_roles
from app.exam_engine import EXAM_DURATION_MINUTES
from app.media_runtime_resolver import resolve_exam_media_batch
from app.models_exam_attempt import ExamAttempt
from app.models_exam_question_trace import ExamQuestionTrace
from app.models_question import Question
from app.models_user import User
from app.question_i18n import resolve_question_content
from app.routers.exams import _assert_attempt_access, _require_official_trace


class ExamMediaQuestionItem(BaseModel):
    """Question candidate-safe enriched with the resolved runtime media."""

    id: str
    number: int
    category: str
    text: str
    options: list[str]
    media_url: str | None = None
    media_type: str | None = None
    media_alt: str | None = None
    audio_url: str | None = None
    poster_url: str | None = None
    fallback_url: str | None = None
    fallback_media_type: str | None = None


class ExamMediaQuestionsRead(BaseModel):
    attempt_id: str
    questions: list[ExamMediaQuestionItem]
    duration_seconds: int = 1800
    threshold: int = 35


router = APIRouter(prefix="/exams", tags=["exams"])


@router.get("/{attempt_id}/questions", response_model=ExamMediaQuestionsRead)
def get_exam_questions_with_runtime_media(
    attempt_id: str,
    lang: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("center", "candidate", "admin", "super_admin")),
) -> ExamMediaQuestionsRead:
    attempt = db.scalar(select(ExamAttempt).where(ExamAttempt.id == attempt_id))
    if not attempt:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attempt not found")

    _assert_attempt_access(db, current_user, attempt)

    if attempt.status in ("submitted", "passed", "failed", "cancelled"):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Exam already {attempt.status} — questions no longer accessible",
        )

    trace = _require_official_trace(
        db.scalar(select(ExamQuestionTrace).where(ExamQuestionTrace.attempt_id == attempt_id))
    )
    questions = list(
        db.scalars(select(Question).where(Question.id.in_(trace.question_ids))).all()
    )
    if len(questions) != trace.question_count:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "OFFICIAL_EXAM_TRACE_INCOMPLETE",
                "message": "Certaines questions de la trace officielle sont introuvables.",
            },
        )

    id_order = {question_id: index for index, question_id in enumerate(trace.question_ids)}
    questions.sort(key=lambda question: id_order.get(question.id, 999))

    resolved_media = {
        item.question_id: item
        for item in resolve_exam_media_batch(db, trace.question_ids)
    }

    items: list[ExamMediaQuestionItem] = []
    for index, question in enumerate(questions):
        content = resolve_question_content(question, lang)
        media = resolved_media.get(question.id)
        items.append(
            ExamMediaQuestionItem(
                id=question.id,
                number=index + 1,
                category=question.category,
                text=content["text"],
                options=content["options"] if isinstance(content["options"], list) else [],
                media_url=media.media_url if media else None,
                media_type=media.media_type if media else None,
                media_alt=media.media_alt if media else None,
                audio_url=content.get("audio_url"),
                poster_url=media.poster_url if media else None,
                fallback_url=media.fallback_url if media else None,
                fallback_media_type=media.fallback_media_type if media else None,
            )
        )

    return ExamMediaQuestionsRead(
        attempt_id=attempt_id,
        questions=items,
        duration_seconds=EXAM_DURATION_MINUTES * 60,
        threshold=35,
    )
