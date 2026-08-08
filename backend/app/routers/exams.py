import csv
import io
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel as _BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.deps import require_roles
from app.exam_attempt_locking import RECOVERABLE_ATTEMPT_STATUSES, find_latest_attempt, lock_exam_attempt
from app.exam_engine import (
    EXAM_DURATION_MINUTES,
    EXAM_QUESTIONS_TOTAL,
    build_question_bank_hash,
    build_score_summary,
    build_selected_questions_hash,
    score_answers,
    select_exam_questions,
)
from app.models_audit import AuditLog
from app.models_booking import Booking
from app.models_candidate import Candidate
from app.models_center import Center
from app.models_device_session import DeviceSession
from app.models_exam_attempt import ExamAttempt
from app.models_exam_question_trace import ExamQuestionTrace
from app.models_question import Question
from app.models_session import ExamSession
from app.models_user import User
from app.pdf_service import build_result_certificate_pdf
from app.schemas import ExamAttemptRead, ExamCertificateVerificationRead, ExamStartFromBookingRequest, ExamStartRequest, ExamSubmitRequest
from app.sentry import capture_exception as _sentry_cap
from app.sentry import capture_exception as _sentry_capture


class ExamQuestionItem(_BaseModel):
    """Question telle que vue par le candidat — sans la réponse correcte."""
    id: str
    number: int
    category: str
    text: str
    options: list[str]
    media_url: str | None = None
    media_type: str | None = None  # 'sign' | 'scene' | None
    # Enregistrement audio dans la langue du candidat (locuteur natif).
    # Absent → le client utilise la synthèse vocale en repli.
    audio_url: str | None = None


class ExamQuestionsRead(_BaseModel):
    attempt_id: str
    questions: list[ExamQuestionItem]
    duration_seconds: int = 1800   # 30 min par défaut
    threshold: int = 35


router = APIRouter(prefix="/exams", tags=["exams"])


def _is_attempt_expired(attempt: ExamAttempt, now: datetime) -> bool:
    return now - attempt.started_at > timedelta(minutes=EXAM_DURATION_MINUTES)


def _assert_center_session_access(current_user: User, session: ExamSession | None) -> None:
    """Empêche un agent centre d'opérer sur une session d'un autre centre."""
    if current_user.role != "center":
        return
    if session and current_user.center_id and session.center_id == current_user.center_id:
        return
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Cette session appartient à un autre centre.",
    )


def _assert_attempt_access(db: Session, current_user: User, attempt: ExamAttempt) -> None:
    """Protège toutes les ressources d'une tentative contre les accès horizontaux."""
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
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cette tentative ne vous appartient pas.",
        )

    if current_user.role == "center":
        session = db.get(ExamSession, attempt.session_id)
        _assert_center_session_access(current_user, session)
        return

    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Accès refusé.")


def _require_official_bank_ready(approved: list[Question]) -> None:
    """Refuse de démarrer un examen officiel avec une banque non homologuée.

    Un manque de contenu approuvé est un incident de préparation de la banque,
    jamais une raison de retomber silencieusement sur des questions non validées.
    """
    if len(approved) >= EXAM_QUESTIONS_TOTAL:
        return
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail={
            "code": "OFFICIAL_QUESTION_BANK_NOT_READY",
            "message": "La banque officielle ne contient pas assez de questions approuvées pour démarrer l'examen.",
            "approved_questions": len(approved),
            "required_questions": EXAM_QUESTIONS_TOTAL,
        },
    )


def _require_official_trace(trace: ExamQuestionTrace | None) -> ExamQuestionTrace:
    """Toute lecture ou notation officielle doit reposer sur la trace créée au départ."""
    if trace and trace.question_ids:
        return trace
    raise HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail={
            "code": "OFFICIAL_EXAM_TRACE_MISSING",
            "message": "La trace officielle de cette tentative est introuvable. Aucune reconstruction automatique n'est autorisée.",
        },
    )


def _create_exam_attempt(
    db: Session, candidate_id: str, session_id: str, *, commit: bool = True
) -> ExamAttempt:
    # Un examen officiel tire EXCLUSIVEMENT des questions actives et approuvées.
    approved = list(db.scalars(
        select(Question).where(
            Question.is_active.is_(True),
            Question.validation_status == "approved",
        )
    ).all())
    _require_official_bank_ready(approved)

    selected = select_exam_questions(approved)
    if len(selected) != EXAM_QUESTIONS_TOTAL:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "OFFICIAL_QUESTION_SELECTION_INCOMPLETE",
                "message": "La banque approuvée ne permet pas de constituer un examen officiel complet.",
                "selected_questions": len(selected),
                "required_questions": EXAM_QUESTIONS_TOTAL,
            },
        )

    attempt = ExamAttempt(candidate_id=candidate_id, session_id=session_id)
    db.add(attempt)
    db.flush()

    question_ids = [q.id for q in selected]
    bank_hash = build_question_bank_hash(approved)
    selection_hash = build_selected_questions_hash(selected)
    version_label = f"official-{bank_hash[:12]}"
    trace = ExamQuestionTrace(
        attempt_id=attempt.id,
        question_ids=question_ids,
        question_count=len(question_ids),
        bank_hash=bank_hash,
        version_label=f"{version_label}|sel-{selection_hash[:12]}",
        selection_mode="official_category_distribution",
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
            },
        )
    )
    if commit:
        db.commit()
        db.refresh(attempt)
    else:
        db.flush()
    return attempt


def _register_exam_start_device(
    db: Session,
    attempt: ExamAttempt,
    session: ExamSession,
    device_key: str | None,
    device_label: str | None = None,
) -> None:
    if not device_key:
        return
    normalized_device_key = device_key.strip()
    now = datetime.now(UTC).replace(tzinfo=None)
    duplicate = db.scalar(
        select(DeviceSession).where(
            DeviceSession.center_id == session.center_id,
            DeviceSession.session_id == session.id,
            DeviceSession.device_key == normalized_device_key,
            DeviceSession.status.in_(["active", "suspicious"]),
        )
    )
    status_label = "active"
    risk_reason = None
    if duplicate and duplicate.attempt_id != attempt.id:
        duplicate.status = "suspicious"
        duplicate.risk_reason = "same_device_key_used_for_multiple_attempts"
        duplicate.last_seen_at = now
        db.add(duplicate)
        status_label = "suspicious"
        risk_reason = "same_device_key_used_for_multiple_attempts"

    device_session = DeviceSession(
        center_id=session.center_id,
        session_id=session.id,
        attempt_id=attempt.id,
        device_key=normalized_device_key,
        device_label=device_label,
        status=status_label,
        risk_reason=risk_reason,
        last_seen_at=now,
    )
    db.add(device_session)
    db.flush()
    db.add(
        AuditLog(
            actor_id=None,
            action="exam.device_session_started" if status_label == "active" else "exam.device_session_suspicious",
            entity="device_session",
            entity_id=device_session.id,
            details={
                "attempt_id": attempt.id,
                "candidate_id": attempt.candidate_id,
                "session_id": session.id,
                "center_id": session.center_id,
                "device_key": normalized_device_key,
                "status": status_label,
                "risk_reason": risk_reason,
                "duplicate_device_session_id": duplicate.id if duplicate else None,
            },
        )
    )


def _write_exam_guard_log(
    db: Session,
    attempt: ExamAttempt,
    action: str,
    reason: str,
    checked_at: datetime,
    extra_details: dict | None = None,
) -> None:
    details = {
        "candidate_id": attempt.candidate_id,
        "session_id": attempt.session_id,
        "attempt_status": attempt.status,
        "reason": reason,
        "started_at": attempt.started_at.isoformat(),
        "submitted_at": attempt.submitted_at.isoformat() if attempt.submitted_at else None,
        "checked_at": checked_at.isoformat(),
    }
    if extra_details:
        details.update(extra_details)
    db.add(
        AuditLog(
            actor_id=None,
            action=action,
            entity="exam_attempt",
            entity_id=attempt.id,
            details=details,
        )
    )


def _write_certificate_verification_log(
    db: Session,
    attempt_id: str,
    valid: bool,
    status_label: str,
    checked_at: datetime,
    reason: str | None = None,
    extra_details: dict | None = None,
) -> None:
    details = {
        "valid": valid,
        "status": status_label,
        "reason": reason,
        "checked_at": checked_at.isoformat(),
    }
    if extra_details:
        details.update(extra_details)
    db.add(
        AuditLog(
            actor_id=None,
            action="certificate.verify",
            entity="exam_certificate",
            entity_id=attempt_id,
            details=details,
        )
    )


@router.post("/start", response_model=ExamAttemptRead, status_code=status.HTTP_201_CREATED)
def start_exam(
    payload: ExamStartRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("center", "admin", "super_admin")),
) -> ExamAttempt:
    if current_user.role == "center":
        _assert_center_session_access(current_user, db.get(ExamSession, payload.session_id))
    return _create_exam_attempt(db, payload.candidate_id, payload.session_id)


@router.post("/start-from-booking", response_model=ExamAttemptRead, status_code=status.HTTP_201_CREATED)
def start_exam_from_booking(
    payload: ExamStartFromBookingRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("candidate", "center", "admin", "super_admin")),
) -> ExamAttempt:
    booking = db.scalar(
        select(Booking)
        .where(Booking.reference == payload.booking_reference)
        .with_for_update()
    )
    if not booking:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found")

    if current_user.role == "candidate":
        cand = db.get(Candidate, booking.candidate_id)
        owns = cand is not None and (
            cand.user_id == current_user.id
            or bool(cand.email and cand.email == current_user.email)
        )
        if not owns:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cette réservation ne vous appartient pas.",
            )

    if booking.status not in {"confirmed", "paid", "checked_in"}:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Booking is not eligible for exam start")
    session = db.get(ExamSession, booking.session_id)
    if not session:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Incomplete booking session")
    _assert_center_session_access(current_user, session)

    latest_attempt = find_latest_attempt(db, booking.candidate_id, booking.session_id)
    if latest_attempt is not None and latest_attempt.status in RECOVERABLE_ATTEMPT_STATUSES:
        _assert_attempt_access(db, current_user, latest_attempt)
        _register_exam_start_device(
            db, latest_attempt, session, payload.device_key, payload.device_label
        )
        db.add(
            AuditLog(
                actor_id=current_user.id,
                action="exam.attempt_resumed",
                entity="exam_attempt",
                entity_id=latest_attempt.id,
                details={
                    "booking_reference": booking.reference,
                    "candidate_id": booking.candidate_id,
                    "session_id": booking.session_id,
                    "attempt_status": latest_attempt.status,
                    "recovery_mode": "booking_retry_or_device_replacement",
                },
            )
        )
        db.commit()
        db.refresh(latest_attempt)
        return latest_attempt

    if latest_attempt is not None:
        code = "EXAM_ATTEMPT_BLOCKED_BY_INCIDENT" if latest_attempt.status == "incident_blocked" else "BOOKING_ALREADY_USED_FOR_EXAM"
        message = (
            "Cette tentative est bloquée par un incident. Une décision administrateur est requise."
            if latest_attempt.status == "incident_blocked"
            else "Cette réservation a déjà été utilisée pour un examen. Un nouveau passage exige un rattrapage institutionnel autorisé."
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": code,
                "message": message,
                "attempt_id": latest_attempt.id,
                "attempt_status": latest_attempt.status,
            },
        )

    attempt = _create_exam_attempt(db, booking.candidate_id, booking.session_id)
    _register_exam_start_device(db, attempt, session, payload.device_key, payload.device_label)
    db.commit()
    db.refresh(attempt)
    return attempt


@router.get("/{attempt_id}/questions", response_model=ExamQuestionsRead)
def get_exam_questions(
    attempt_id: str,
    lang: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("center", "candidate", "admin", "super_admin")),
) -> ExamQuestionsRead:
    """Retourne les questions de la trace officielle sans la réponse correcte."""
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
    questions = list(db.scalars(
        select(Question).where(Question.id.in_(trace.question_ids))
    ).all())
    if len(questions) != trace.question_count:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "OFFICIAL_EXAM_TRACE_INCOMPLETE",
                "message": "Certaines questions de la trace officielle sont introuvables.",
            },
        )
    id_order = {qid: i for i, qid in enumerate(trace.question_ids)}
    questions.sort(key=lambda q: id_order.get(q.id, 999))

    from app.question_i18n import resolve_question_content

    items = []
    for i, q in enumerate(questions):
        content = resolve_question_content(q, lang)
        items.append(ExamQuestionItem(
            id=q.id,
            number=i + 1,
            category=q.category,
            text=content["text"],
            options=content["options"] if isinstance(content["options"], list) else [],
            media_url=getattr(q, "media_url", None),
            media_type=getattr(q, "media_type", None),
            audio_url=content.get("audio_url"),
        ))

    return ExamQuestionsRead(
        attempt_id=attempt_id,
        questions=items,
        duration_seconds=EXAM_DURATION_MINUTES * 60,
        threshold=35,
    )


@router.get("/summary")
def get_exam_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "super_admin")),
) -> dict:
    attempts = db.scalars(select(ExamAttempt)).all()
    submitted = [attempt for attempt in attempts if attempt.status == "submitted"]
    passed = [attempt for attempt in submitted if attempt.passed]
    failed = [attempt for attempt in submitted if attempt.passed is False]
    average_score = 0
    if submitted:
        scores = [attempt.score or 0 for attempt in submitted]
        average_score = round(sum(scores) / len(scores), 2)
    return {
        "total_attempts": len(attempts),
        "submitted_attempts": len(submitted),
        "passed_attempts": len(passed),
        "failed_attempts": len(failed),
        "average_score": average_score,
    }


@router.get("/export.csv")
def export_exam_attempts_csv(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "super_admin")),
) -> Response:
    attempts = db.scalars(select(ExamAttempt).order_by(ExamAttempt.started_at.desc())).all()
    output = io.StringIO()
    writer = csv.writer(output, delimiter=";")
    writer.writerow([
        "attempt_id",
        "candidate_reference",
        "candidate_name",
        "permit_category",
        "session_reference",
        "center_code",
        "center_name",
        "center_city",
        "status",
        "score",
        "passed",
        "started_at",
        "submitted_at",
    ])
    for attempt in attempts:
        candidate = db.get(Candidate, attempt.candidate_id)
        session = db.get(ExamSession, attempt.session_id)
        center = db.get(Center, session.center_id) if session else None
        writer.writerow([
            attempt.id,
            candidate.reference if candidate else "",
            f"{candidate.first_name} {candidate.last_name}" if candidate else "",
            candidate.permit_category if candidate else "",
            session.reference if session else "",
            center.code if center else "",
            center.name if center else "",
            center.city if center else "",
            attempt.status,
            attempt.score if attempt.score is not None else "",
            str(attempt.passed).lower() if attempt.passed is not None else "",
            attempt.started_at.isoformat() if attempt.started_at else "",
            attempt.submitted_at.isoformat() if attempt.submitted_at else "",
        ])
    audit_log = AuditLog(
        actor_id=current_user.id,
        action="exams.export_csv",
        entity="exam_attempt",
        entity_id="national-exam-attempts",
        details={
            "format": "csv",
            "attempts_exported": len(attempts),
            "submitted_attempts": len([attempt for attempt in attempts if attempt.status == "submitted"]),
        },
    )
    db.add(audit_log)
    db.commit()
    headers = {"Content-Disposition": "attachment; filename=coderoute-exam-attempts.csv"}
    return Response(content=output.getvalue(), media_type="text/csv", headers=headers)


@router.post("/{attempt_id}/submit", response_model=ExamAttemptRead)
def submit_exam(
    attempt_id: str,
    payload: ExamSubmitRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("candidate", "center", "admin", "super_admin")),
) -> ExamAttempt:
    attempt = lock_exam_attempt(db, attempt_id)
    if not attempt:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exam attempt not found")

    _assert_attempt_access(db, current_user, attempt)

    now = datetime.now(UTC).replace(tzinfo=None)
    if attempt.status == "submitted":
        _write_exam_guard_log(db, attempt, "exam.replay_submission", "already_submitted", now)
        db.commit()
        db.refresh(attempt)
        return attempt
    if attempt.status == "expired":
        _write_exam_guard_log(db, attempt, "exam.expired_submission_replay", "already_expired", now)
        db.commit()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Exam attempt expired")
    if attempt.status != "started":
        _write_exam_guard_log(db, attempt, "exam.non_active_submission", "invalid_status", now)
        db.commit()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Exam attempt is not active")

    if _is_attempt_expired(attempt, now):
        attempt.status = "expired"
        attempt.submitted_at = now
        _write_exam_guard_log(
            db,
            attempt,
            "exam.late_submission",
            "duration_exceeded",
            now,
            {"duration_minutes": EXAM_DURATION_MINUTES},
        )
        db.add(attempt)
        db.commit()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Exam attempt expired")

    trace = _require_official_trace(
        db.scalar(select(ExamQuestionTrace).where(ExamQuestionTrace.attempt_id == attempt.id))
    )
    questions = list(db.scalars(select(Question).where(Question.id.in_(trace.question_ids))).all())
    if len(questions) != trace.question_count:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "OFFICIAL_EXAM_TRACE_INCOMPLETE",
                "message": "La notation est bloquée car la trace officielle est incomplète.",
            },
        )

    answer_key = {question.id: question.correct_answer for question in questions}
    sanitized_answers = {
        question_id: answer
        for question_id, answer in payload.answers.items()
        if question_id in set(trace.question_ids)
    }
    result = score_answers(answer_key, sanitized_answers)

    candidate = db.get(Candidate, attempt.candidate_id)
    summary = build_score_summary(
        result,
        candidate_name=f"{candidate.first_name} {candidate.last_name}" if candidate else "",
    )

    attempt.answers = sanitized_answers
    attempt.score = result["correct_answers"]
    attempt.passed = result["passed"]
    attempt.status = "submitted"
    attempt.submitted_at = now
    db.add(attempt)

    _cand = db.get(Candidate, attempt.candidate_id)
    if _cand and hasattr(_cand, "attempt_count"):
        _cand.attempt_count = (_cand.attempt_count or 0) + 1
        db.add(_cand)
    from app.audit_chain import append_audit
    append_audit(db,
        actor_id=current_user.id,
        action="exam.submitted",
        entity="exam_attempt",
        entity_id=attempt.id,
        details={
            "candidate_id": attempt.candidate_id,
            "session_id": attempt.session_id,
            "score": result["correct_answers"],
            "total": result["total_questions"],
            "score_percent": result["score_percent"],
            "passed": result["passed"],
            "unanswered": result["unanswered"],
            "summary": summary,
        },
    )
    db.commit()
    db.refresh(attempt)

    try:
        if candidate and candidate.email:
            cert_url = None
            if result["passed"]:
                cert_url = f"https://api.coderoute.gov.gn/api/v1/exams/{attempt.id}/certificate/verify"
            from app.email_service import send_exam_result
            send_exam_result(
                to_email=candidate.email,
                candidate_name=f"{candidate.first_name} {candidate.last_name}",
                booking_reference=attempt.booking_reference if hasattr(attempt, "booking_reference") else attempt.id,
                passed=result["passed"],
                score=result["correct_answers"],
                total=result["total_questions"],
                certificate_url=cert_url,
            )
    except Exception as _sentry_exc:
        _sentry_capture(_sentry_exc, context={"file": __file__, "endpoint": "submit_exam_email"})

    try:
        if candidate and candidate.phone:
            from app.orange_sms import send_exam_result_sms
            send_exam_result_sms(
                phone=candidate.phone,
                candidate_name=f"{candidate.first_name} {candidate.last_name}",
                passed=result["passed"],
                score=result["correct_answers"],
                total=result["total_questions"],
            )
    except Exception as _sms_exc:
        _sentry_cap(_sms_exc, context={"endpoint": "submit_exam_sms"})

    try:
        if candidate and candidate.phone:
            from app.whatsapp_service import send_exam_result_whatsapp
            send_exam_result_whatsapp(
                phone=candidate.phone,
                candidate_name=f"{candidate.first_name} {candidate.last_name}",
                passed=result["passed"],
                score=result["correct_answers"],
                total=result["total_questions"],
            )
    except Exception as _wa_exc:
        _sentry_cap(_wa_exc, context={"endpoint": "submit_exam_whatsapp"})

    return attempt


@router.get("/{attempt_id}/status")
def get_exam_status(
    attempt_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("candidate", "center", "admin", "super_admin")),
) -> dict:
    """Statut temps réel et horloge de référence de la tentative."""
    attempt = db.get(ExamAttempt, attempt_id)
    if not attempt:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exam attempt not found")

    _assert_attempt_access(db, current_user, attempt)

    now = datetime.now(UTC).replace(tzinfo=None)
    elapsed_seconds = int((now - attempt.started_at).total_seconds())
    total_seconds = EXAM_DURATION_MINUTES * 60
    remaining_seconds = max(0, total_seconds - elapsed_seconds)

    trace = db.scalar(select(ExamQuestionTrace).where(ExamQuestionTrace.attempt_id == attempt.id))
    question_count = trace.question_count if trace else 0

    is_expired = remaining_seconds == 0 and attempt.status == "started"
    if is_expired:
        attempt.status = "expired"
        attempt.submitted_at = now
        db.add(attempt)
        db.commit()

    return {
        "attempt_id": attempt.id,
        "status": attempt.status,
        "elapsed_seconds": elapsed_seconds,
        "remaining_seconds": remaining_seconds,
        "total_seconds": total_seconds,
        "question_count": question_count,
        "started_at": attempt.started_at.isoformat() if attempt.started_at else None,
        "submitted_at": attempt.submitted_at.isoformat() if attempt.submitted_at else None,
        "score": attempt.score if attempt.status == "submitted" else None,
        "passed": attempt.passed if attempt.status == "submitted" else None,
        "expired": is_expired or attempt.status == "expired",
    }


@router.get("/{attempt_id}/results")
def get_exam_results(
    attempt_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("candidate", "center", "admin", "super_admin")),
) -> dict:
    """Résultats détaillés uniquement après soumission et selon le périmètre d'accès."""
    attempt = db.get(ExamAttempt, attempt_id)
    if not attempt:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exam attempt not found")

    _assert_attempt_access(db, current_user, attempt)

    if attempt.status != "submitted":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Résultats disponibles seulement après soumission",
        )

    trace = _require_official_trace(
        db.scalar(select(ExamQuestionTrace).where(ExamQuestionTrace.attempt_id == attempt.id))
    )
    questions = list(db.scalars(select(Question).where(Question.id.in_(trace.question_ids))).all())
    if len(questions) != trace.question_count:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Trace officielle incomplète")
    order_map = {qid: i for i, qid in enumerate(trace.question_ids)}
    questions.sort(key=lambda q: order_map.get(q.id, 9999))

    submitted = attempt.answers or {}
    items = []
    for i, q in enumerate(questions):
        given = submitted.get(q.id)
        correct = q.correct_answer
        items.append({
            "number": i + 1,
            "question_id": q.id,
            "category": q.category,
            "text": q.text,
            "options": q.options,
            "given_answer": given,
            "correct_answer": correct,
            "is_correct": given == correct,
            "explanation": q.explanation,
        })

    candidate = db.get(Candidate, attempt.candidate_id)
    from app.exam_engine import EXAM_PASS_THRESHOLD
    return {
        "attempt_id": attempt.id,
        "candidate_name": f"{candidate.first_name} {candidate.last_name}" if candidate else "",
        "score": attempt.score,
        "total": trace.question_count,
        "score_percent": round((attempt.score or 0) / trace.question_count * 100, 2) if trace.question_count else 0,
        "passed": attempt.passed,
        "threshold": EXAM_PASS_THRESHOLD,
        "submitted_at": attempt.submitted_at.isoformat() if attempt.submitted_at else None,
        "questions": items,
    }


@router.get("/{attempt_id}/certificate/verify", response_model=ExamCertificateVerificationRead)
def verify_exam_certificate(attempt_id: str, db: Session = Depends(get_db)) -> ExamCertificateVerificationRead:
    checked_at = datetime.now(UTC).replace(tzinfo=None)
    attempt = db.get(ExamAttempt, attempt_id)
    if not attempt:
        _write_certificate_verification_log(
            db,
            attempt_id=attempt_id,
            valid=False,
            status_label="not_found",
            checked_at=checked_at,
            reason="Tentative d'examen introuvable",
        )
        db.commit()
        return ExamCertificateVerificationRead(
            valid=False,
            attempt_id=attempt_id,
            status="not_found",
            reason="Tentative d'examen introuvable",
        )
    if attempt.status != "submitted":
        _write_certificate_verification_log(
            db,
            attempt_id=attempt.id,
            valid=False,
            status_label=attempt.status,
            checked_at=checked_at,
            reason="Tentative d'examen non soumise",
        )
        db.commit()
        return ExamCertificateVerificationRead(
            valid=False,
            attempt_id=attempt.id,
            status=attempt.status,
            reason="Tentative d'examen non soumise",
        )

    candidate = db.get(Candidate, attempt.candidate_id)
    session = db.get(ExamSession, attempt.session_id)
    center = db.get(Center, session.center_id) if session else None
    if not candidate or not session or not center:
        _write_certificate_verification_log(
            db,
            attempt_id=attempt.id,
            valid=False,
            status_label="incomplete",
            checked_at=checked_at,
            reason="Donnees du certificat incompletes",
        )
        db.commit()
        return ExamCertificateVerificationRead(
            valid=False,
            attempt_id=attempt.id,
            status="incomplete",
            reason="Donnees du certificat incompletes",
        )

    _write_certificate_verification_log(
        db,
        attempt_id=attempt.id,
        valid=True,
        status_label=attempt.status,
        checked_at=checked_at,
        reason="Certificat authentique",
        extra_details={
            "candidate_reference": candidate.reference,
            "session_reference": session.reference,
            "center_name": center.name,
            "score": attempt.score,
            "passed": attempt.passed,
        },
    )
    db.commit()
    return ExamCertificateVerificationRead(
        valid=True,
        attempt_id=attempt.id,
        status=attempt.status,
        candidate_reference=candidate.reference,
        candidate_name=f"{candidate.first_name} {candidate.last_name}",
        identity_number=None,
        permit_category=candidate.permit_category,
        session_reference=session.reference,
        center_name=center.name,
        center_city=center.city,
        score=attempt.score,
        passed=attempt.passed,
        submitted_at=attempt.submitted_at.isoformat() if attempt.submitted_at else None,
    )


@router.get("/{attempt_id}/certificate.pdf")
def get_exam_certificate(
    attempt_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("candidate", "center", "admin", "super_admin")),
) -> Response:
    attempt = db.get(ExamAttempt, attempt_id)
    if not attempt:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exam attempt not found")

    _assert_attempt_access(db, current_user, attempt)

    if attempt.status != "submitted":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Exam attempt not submitted")

    candidate = db.get(Candidate, attempt.candidate_id)
    session = db.get(ExamSession, attempt.session_id)
    center = db.get(Center, session.center_id) if session else None
    if not candidate or not session or not center:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Incomplete certificate data")

    pdf = build_result_certificate_pdf(
        candidate={
            "reference": candidate.reference,
            "full_name": f"{candidate.first_name} {candidate.last_name}",
            "identity_number": candidate.identity_number,
            "permit_category": candidate.permit_category,
        },
        session={"reference": session.reference, "starts_at": session.starts_at.isoformat()},
        center={"name": center.name, "city": center.city},
        attempt={
            "score": attempt.score,
            "passed": attempt.passed,
            "status": attempt.status,
            "submitted_at": attempt.submitted_at.isoformat() if attempt.submitted_at else None,
        },
    )
    headers = {"Content-Disposition": f"attachment; filename=coderoute-result-{attempt.id}.pdf"}
    return Response(content=pdf, media_type="application/pdf", headers=headers)
