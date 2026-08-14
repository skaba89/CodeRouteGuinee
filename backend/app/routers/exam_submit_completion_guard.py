"""Guard de complétude pour la soumission manuelle d'un examen officiel.

La finalisation automatique à expiration reste portée par son endpoint dédié.
Cette façade ne change ni le scoring ni les notifications : elle fusionne la
copie autosauvegardée avec le payload final, exige une réponse pour chaque
question de la trace officielle, puis délègue au moteur historique.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.deps import require_roles
from app.exam_attempt_locking import lock_exam_attempt
from app.exam_engine import EXAM_DURATION_MINUTES
from app.models_audit import AuditLog
from app.models_exam_attempt import ExamAttempt
from app.models_exam_question_trace import ExamQuestionTrace
from app.models_user import User
from app.schemas import ExamAttemptRead, ExamSubmitRequest


router = APIRouter(prefix="/exams", tags=["exams"])


def _sanitize_answers(answers: dict | None, trace_ids: set[str]) -> dict[str, str]:
    if not isinstance(answers, dict):
        return {}
    return {
        str(question_id): answer
        for question_id, answer in answers.items()
        if str(question_id) in trace_ids and isinstance(answer, str)
    }


@router.post("/{attempt_id}/submit", response_model=ExamAttemptRead)
def submit_complete_exam(
    attempt_id: str,
    payload: ExamSubmitRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("candidate", "center", "admin", "super_admin")),
) -> ExamAttempt:
    # Import différé : ce module est monté depuis app.routers.__init__ après le
    # routeur historique. Cela évite une dépendance circulaire au bootstrap.
    from app.routers import exams as legacy_exams

    attempt = lock_exam_attempt(db, attempt_id)
    if not attempt:
        # Conserver exactement le contrat 404 historique.
        return legacy_exams.submit_exam(attempt_id, payload, db, current_user)

    # Ne jamais inspecter ni révéler la trace d'une tentative non autorisée.
    legacy_exams._assert_attempt_access(db, current_user, attempt)

    # Idempotence, statuts invalides et expiration restent la responsabilité du
    # moteur historique. En particulier, une expiration ne doit jamais être
    # transformée en erreur "réponses manquantes".
    now = datetime.now(UTC).replace(tzinfo=None)
    if attempt.status != "started" or now - attempt.started_at > timedelta(minutes=EXAM_DURATION_MINUTES):
        return legacy_exams.submit_exam(attempt_id, payload, db, current_user)

    trace = db.scalar(
        select(ExamQuestionTrace).where(ExamQuestionTrace.attempt_id == attempt.id)
    )
    if trace is None or not trace.question_ids:
        # Préserver le code d'erreur OFFICIAL_EXAM_TRACE_MISSING historique.
        return legacy_exams.submit_exam(attempt_id, payload, db, current_user)

    trace_ids = set(trace.question_ids)
    saved_answers = _sanitize_answers(attempt.answers, trace_ids)
    payload_answers = _sanitize_answers(payload.answers, trace_ids)
    effective_answers = {**saved_answers, **payload_answers}
    missing_count = sum(1 for question_id in trace.question_ids if question_id not in effective_answers)

    if missing_count:
        answered_count = trace.question_count - missing_count
        db.add(
            AuditLog(
                actor_id=current_user.id,
                action="exam.incomplete_submission",
                entity="exam_attempt",
                entity_id=attempt.id,
                details={
                    "candidate_id": attempt.candidate_id,
                    "session_id": attempt.session_id,
                    "reason": "missing_answers",
                    "answered_questions": answered_count,
                    "required_questions": trace.question_count,
                    "missing_count": missing_count,
                },
            )
        )
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "EXAM_INCOMPLETE_ANSWERS",
                "message": "Toutes les questions doivent être répondues avant la soumission manuelle.",
                "answered_questions": answered_count,
                "required_questions": trace.question_count,
                "missing_count": missing_count,
            },
        )

    # Le moteur historique reste l'unique source de vérité pour le scoring,
    # l'idempotence, l'audit de soumission et les notifications. Le payload final
    # complet réinjecte aussi les réponses déjà autosauvegardées côté serveur.
    merged_payload = ExamSubmitRequest(answers=effective_answers)
    return legacy_exams.submit_exam(attempt_id, merged_payload, db, current_user)
