"""Media-safe creation of new official exam attempts.

The historical exam router remains responsible for authorization, station gates,
submission, scoring and certificates. This service replaces only attempt creation
so a newly created trace cannot contain a missing/broken normalized primary media.
"""
from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.exam_engine import (
    EXAM_QUESTIONS_TOTAL,
    build_question_bank_hash,
    build_selected_questions_hash,
    select_exam_questions,
)
from app.models_audit import AuditLog
from app.models_exam_attempt import ExamAttempt
from app.models_exam_question_trace import ExamQuestionTrace
from app.models_question import Question
from app.official_media_policy import official_media_strict_mode_enabled
from app.official_media_readiness import (
    runtime_ready_official_questions,
    strict_ready_official_questions,
)


def create_media_safe_exam_attempt(
    db: Session,
    candidate_id: str,
    session_id: str,
    *,
    commit: bool = True,
) -> ExamAttempt:
    approved = list(
        db.scalars(
            select(Question).where(
                Question.is_active.is_(True),
                Question.validation_status == "approved",
            )
        ).all()
    )

    strict_mode = official_media_strict_mode_enabled()
    if strict_mode:
        eligible, media_readiness = strict_ready_official_questions(db, approved)
        readiness_mode = "strict_normalized_regulatory"
    else:
        eligible, media_readiness = runtime_ready_official_questions(db, approved)
        readiness_mode = "runtime_compatibility"

    if len(eligible) < EXAM_QUESTIONS_TOTAL:
        message = (
            "La banque officielle ne contient pas assez de questions avec un média normalisé et homologué."
            if strict_mode
            else "La banque officielle ne contient pas assez de questions avec un média candidat exploitable."
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "OFFICIAL_MEDIA_BANK_NOT_READY",
                "message": message,
                "approved_questions": len(approved),
                "runtime_ready_questions": media_readiness["runtime_ready_questions"],
                "strict_ready_questions": media_readiness["strict_ready_questions"],
                "required_questions": EXAM_QUESTIONS_TOTAL,
                "blocked_questions_total": media_readiness["blocked_questions_total"],
                "legacy_migration_required": media_readiness["legacy_migration_required"],
                "strict_mode": strict_mode,
                "media_gate": readiness_mode,
            },
        )

    selected = select_exam_questions(eligible)
    if len(selected) != EXAM_QUESTIONS_TOTAL:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "OFFICIAL_QUESTION_SELECTION_INCOMPLETE",
                "message": "La banque média-compatible ne permet pas de constituer un examen officiel complet.",
                "selected_questions": len(selected),
                "required_questions": EXAM_QUESTIONS_TOTAL,
                "runtime_ready_questions": media_readiness["runtime_ready_questions"],
                "strict_ready_questions": media_readiness["strict_ready_questions"],
                "strict_mode": strict_mode,
                "media_gate": readiness_mode,
            },
        )

    attempt = ExamAttempt(candidate_id=candidate_id, session_id=session_id)
    db.add(attempt)
    db.flush()

    question_ids = [question.id for question in selected]
    bank_hash = build_question_bank_hash(eligible)
    selection_hash = build_selected_questions_hash(selected)
    version_label = f"official-{bank_hash[:12]}"
    trace = ExamQuestionTrace(
        attempt_id=attempt.id,
        question_ids=question_ids,
        question_count=len(question_ids),
        bank_hash=bank_hash,
        version_label=f"{version_label}|sel-{selection_hash[:12]}",
        selection_mode=(
            "official_category_distribution_media_strict"
            if strict_mode
            else "official_category_distribution_media_safe"
        ),
    )
    db.add(trace)
    db.add(
        AuditLog(
            actor_id=None,
            action="exam.question_trace_created",
            entity="exam_question_trace",
            entity_id=trace.id,
            details={
                "attempt_id": attempt.id,
                "candidate_id": attempt.candidate_id,
                "session_id": attempt.session_id,
                "question_count": len(question_ids),
                "bank_hash": bank_hash,
                "version_label": trace.version_label,
                "approved_bank_size": len(approved),
                "runtime_ready_bank_size": media_readiness["runtime_ready_questions"],
                "strict_ready_bank_size": media_readiness["strict_ready_questions"],
                "eligible_bank_size": len(eligible),
                "legacy_migration_required": media_readiness["legacy_migration_required"],
                "strict_mode": strict_mode,
                "media_gate": readiness_mode,
            },
        )
    )
    if commit:
        db.commit()
        db.refresh(attempt)
    else:
        db.flush()
    return attempt
