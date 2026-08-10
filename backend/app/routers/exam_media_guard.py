"""Candidate-safe media facade for the official exam question endpoint.

This guard replaces only ``GET /exams/{attempt_id}/questions`` at router
aggregation time. All scoring, submission, timeout, certificate and center
security endpoints continue to be served by ``routers.exams`` unchanged.

The media resolver is the only source of candidate-facing media here:
validated normalized media -> controlled legacy fallback -> none.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.deps import require_roles
from app.media_runtime_resolver import ResolvedExamMedia, resolve_exam_media_batch
from app.models_exam_attempt import ExamAttempt
from app.models_exam_question_trace import ExamQuestionTrace
from app.models_question import Question
from app.models_user import User
from app.question_i18n import resolve_question_content
from app.routers.exams import (
    EXAM_DURATION_MINUTES,
    _assert_attempt_access,
    _require_official_trace,
)

router = APIRouter(prefix="/exams", tags=["exams"])


class ResolvedExamQuestionItem(BaseModel):
    """Question candidate-safe: never contains answer/explanation/licence metadata."""

    id: str
    number: int
    category: str
    text: str
    options: list[str]
    media_url: str | None = None
    media_type: str | None = None
    media_alt: str | None = None
    media_poster_url: str | None = None
    media_fallback_url: str | None = None
    media_source: str = "none"
    media_degraded: bool = False
    audio_url: str | None = None


class ResolvedExamQuestionsRead(BaseModel):
    attempt_id: str
    questions: list[ResolvedExamQuestionItem]
    duration_seconds: int = EXAM_DURATION_MINUTES * 60
    threshold: int = 35


def _media_by_question_id(db: Session, question_ids: list[str]) -> dict[str, ResolvedExamMedia]:
    return {
        media.question_id: media
        for media in resolve_exam_media_batch(db, question_ids)
    }


@router.get("/{attempt_id}/questions", response_model=ResolvedExamQuestionsRead)
def get_exam_questions_with_resolved_media(
    attempt_id: str,
    lang: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("center", "candidate", "admin", "super_admin")),
) -> ResolvedExamQuestionsRead:
    """Serve the immutable official trace with candidate-safe resolved media.

    The endpoint deliberately preserves the historical response fields while
    adding poster/fallback diagnostics for upgraded clients. It never exposes
    ``correct_answer``, media provenance, licence details or authority evidence.
    """

    attempt = db.scalar(select(ExamAttempt).where(ExamAttempt.id == attempt_id))
    if not attempt:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attempt not found")

    _assert_attempt_access(db, current_user, attempt)

    if attempt.status in {"submitted", "passed", "failed", "cancelled"}:
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
    media_map = _media_by_question_id(db, [question.id for question in questions])

    items: list[ResolvedExamQuestionItem] = []
    for index, question in enumerate(questions):
        content = resolve_question_content(question, lang)
        media = media_map.get(question.id)
        items.append(
            ResolvedExamQuestionItem(
                id=question.id,
                number=index + 1,
                category=question.category,
                text=content["text"],
                options=content["options"] if isinstance(content["options"], list) else [],
                media_url=media.media_url if media else None,
                media_type=media.media_type if media else None,
                media_alt=media.media_alt if media else None,
                media_poster_url=media.poster_url if media else None,
                media_fallback_url=media.fallback_url if media else None,
                media_source=media.source if media else "none",
                media_degraded=bool(media.degraded) if media else True,
                audio_url=content.get("audio_url"),
            )
        )

    return ResolvedExamQuestionsRead(
        attempt_id=attempt_id,
        questions=items,
        duration_seconds=EXAM_DURATION_MINUTES * 60,
        threshold=35,
    )
