"""Runtime sécurisé des examens officiels.

Ce module complète le routeur historique `exams` avec trois garanties importantes :
- autosauvegarde serveur des réponses pendant l'épreuve ;
- lecture sécurisée de la dernière copie serveur pour la reprise après incident ;
- finalisation à l'expiration à partir de la dernière sauvegarde serveur,
  sans accepter de nouvelles réponses après la limite.
"""
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.deps import require_roles
from app.exam_engine import EXAM_DURATION_MINUTES, build_score_summary, score_answers
from app.models_audit import AuditLog
from app.models_candidate import Candidate
from app.models_exam_attempt import ExamAttempt
from app.models_exam_question_trace import ExamQuestionTrace
from app.models_question import Question
from app.models_session import ExamSession
from app.models_user import User
from app.schemas import ExamAttemptRead, ExamSubmitRequest

router = APIRouter(prefix="/exams", tags=["exams"])


def _assert_runtime_access(db: Session, current_user: User, attempt: ExamAttempt) -> None:
    if current_user.role in {"admin", "super_admin"}:
        return

    if current_user.role == "candidate":
        candidate = db.get(Candidate, attempt.candidate_id)
        owns_attempt = candidate is not None and (
            candidate.user_id == current_user.id
            or bool(candidate.email and candidate.email == current_user.email)
        )
        if owns_attempt:
            return
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cette tentative ne vous appartient pas.")

    if current_user.role == "center":
        session = db.get(ExamSession, attempt.session_id)
        if session and current_user.center_id and session.center_id == current_user.center_id:
            return
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cette tentative appartient à un autre centre.")

    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Accès refusé.")


def _trace_questions(db: Session, attempt: ExamAttempt) -> tuple[ExamQuestionTrace, list[Question]]:
    trace = db.scalar(select(ExamQuestionTrace).where(ExamQuestionTrace.attempt_id == attempt.id))
    if not trace or not trace.question_ids:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Trace officielle de l'examen introuvable.")

    questions = list(db.scalars(select(Question).where(Question.id.in_(trace.question_ids))).all())
    if len(questions) != len(trace.question_ids):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Banque de questions incohérente pour cette tentative.")
    return trace, questions


def _sanitize_trace_answers(trace: ExamQuestionTrace, answers: dict | None) -> dict[str, str]:
    """Ne conserve que les réponses appartenant à la trace officielle.

    Cette fonction est utilisée à l'écriture, à la reprise et à la finalisation,
    afin qu'une ancienne donnée ou une clé injectée hors examen ne puisse jamais
    être renvoyée au candidat ni compter dans les métriques de l'épreuve.
    """
    if not answers:
        return {}
    allowed_ids = set(trace.question_ids or [])
    return {
        str(question_id): str(answer)
        for question_id, answer in answers.items()
        if question_id in allowed_ids and isinstance(answer, str)
    }


def _deadline(attempt: ExamAttempt) -> datetime:
    return attempt.started_at + timedelta(minutes=EXAM_DURATION_MINUTES)


@router.get("/{attempt_id}/answers")
def get_saved_exam_answers(
    attempt_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("candidate", "center", "admin", "super_admin")),
) -> dict:
    """Retourne uniquement la dernière copie serveur autorisée de l'épreuve.

    Aucune bonne réponse, explication ou clé de correction n'est exposée. Cet
    endpoint sert à reconstruire l'état du poste candidat après refresh, crash du
    navigateur ou remplacement contrôlé d'un poste en centre d'examen.
    """
    attempt = db.get(ExamAttempt, attempt_id)
    if not attempt:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exam attempt not found")

    _assert_runtime_access(db, current_user, attempt)
    if attempt.status not in {"started", "expired"}:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Saved answers are available only while the exam can still be recovered",
        )

    trace, _questions = _trace_questions(db, attempt)
    answers = _sanitize_trace_answers(trace, attempt.answers)
    return {
        "attempt_id": attempt.id,
        "answers": answers,
        "saved": len(answers),
        "status": attempt.status,
    }


@router.post("/{attempt_id}/answers")
def save_exam_answers(
    attempt_id: str,
    payload: ExamSubmitRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("candidate", "center", "admin", "super_admin")),
) -> dict:
    """Sauvegarde la copie serveur des réponses d'une tentative active.

    Seules les questions sélectionnées dans la trace officielle sont conservées.
    Une réponse reçue après l'échéance est refusée et ne peut donc pas modifier
    la copie qui servira à la finalisation automatique.
    """
    attempt = db.get(ExamAttempt, attempt_id)
    if not attempt:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exam attempt not found")

    _assert_runtime_access(db, current_user, attempt)
    if attempt.status != "started":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Exam attempt is not active")

    now = datetime.now(UTC).replace(tzinfo=None)
    if now > _deadline(attempt):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Exam attempt expired")

    trace, _questions = _trace_questions(db, attempt)
    sanitized_answers = _sanitize_trace_answers(trace, payload.answers)

    attempt.answers = sanitized_answers
    db.add(attempt)
    db.commit()

    return {
        "attempt_id": attempt.id,
        "saved": len(sanitized_answers),
        "saved_at": now.isoformat(),
        "status": attempt.status,
    }


@router.post("/{attempt_id}/timeout-submit", response_model=ExamAttemptRead)
def timeout_submit_exam(
    attempt_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("candidate", "center", "admin", "super_admin")),
) -> ExamAttempt:
    """Finalise l'épreuve à la limite de temps avec la dernière copie serveur.

    Aucun payload de réponses n'est accepté : le serveur score uniquement ce qui
    a été autosauvegardé avant l'échéance. Une petite fenêtre de 2 secondes avant
    la deadline permet au navigateur synchronisé de déclencher proprement la
    finalisation malgré la latence réseau, sans offrir de temps de réponse en plus.
    """
    attempt = db.get(ExamAttempt, attempt_id)
    if not attempt:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exam attempt not found")

    _assert_runtime_access(db, current_user, attempt)

    if attempt.status == "submitted":
        return attempt
    if attempt.status not in {"started", "expired"}:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Exam attempt cannot be finalized")

    now = datetime.now(UTC).replace(tzinfo=None)
    if now < _deadline(attempt) - timedelta(seconds=2):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Exam time has not elapsed")

    trace, questions = _trace_questions(db, attempt)
    saved_answers = _sanitize_trace_answers(trace, attempt.answers)
    answer_key = {question.id: question.correct_answer for question in questions}
    result = score_answers(answer_key, saved_answers)

    candidate = db.get(Candidate, attempt.candidate_id)
    summary = build_score_summary(
        result,
        candidate_name=f"{candidate.first_name} {candidate.last_name}" if candidate else "",
    )

    attempt.answers = saved_answers
    attempt.score = result["correct_answers"]
    attempt.passed = result["passed"]
    attempt.status = "submitted"
    attempt.submitted_at = now
    if candidate and hasattr(candidate, "attempt_count"):
        candidate.attempt_count = (candidate.attempt_count or 0) + 1
        db.add(candidate)

    db.add(attempt)
    db.add(
        AuditLog(
            actor_id=current_user.id,
            action="exam.timeout_submitted",
            entity="exam_attempt",
            entity_id=attempt.id,
            details={
                "candidate_id": attempt.candidate_id,
                "session_id": attempt.session_id,
                "question_count": trace.question_count,
                "saved_answers": len(saved_answers),
                "score": result["correct_answers"],
                "total": result["total_questions"],
                "passed": result["passed"],
                "unanswered": result["unanswered"],
                "summary": summary,
                "deadline": _deadline(attempt).isoformat(),
                "finalized_at": now.isoformat(),
            },
        )
    )
    db.commit()
    db.refresh(attempt)
    return attempt
