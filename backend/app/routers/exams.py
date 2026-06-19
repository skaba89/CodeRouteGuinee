import csv
import hashlib
import io
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.deps import get_current_user, require_roles
from app.exam_engine import score_answers
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

router = APIRouter(prefix="/exams", tags=["exams"])

EXAM_DURATION_MINUTES = 30


def _is_attempt_expired(attempt: ExamAttempt, now: datetime) -> bool:
    return now - attempt.started_at > timedelta(minutes=EXAM_DURATION_MINUTES)


def _build_question_bank_hash(questions: list[Question]) -> str:
    payload = "|".join(f"{question.id}:{question.correct_answer}:{question.is_active}" for question in questions)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _create_exam_attempt(db: Session, candidate_id: str, session_id: str) -> ExamAttempt:
    questions = list(db.scalars(select(Question).where(Question.is_active.is_(True)).order_by(Question.id)).all())
    attempt = ExamAttempt(candidate_id=candidate_id, session_id=session_id)
    db.add(attempt)
    db.flush()

    question_ids = [question.id for question in questions]
    bank_hash = _build_question_bank_hash(questions)
    version_label = f"active-bank-{bank_hash[:12]}" if question_ids else "active-bank-empty"
    trace = ExamQuestionTrace(
        attempt_id=attempt.id,
        question_ids=question_ids,
        question_count=len(question_ids),
        bank_hash=bank_hash,
        version_label=version_label,
        selection_mode="active_bank_snapshot",
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
            },
        )
    )
    db.commit()
    db.refresh(attempt)
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
    now = datetime.utcnow()
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
    return _create_exam_attempt(db, payload.candidate_id, payload.session_id)


@router.post("/start-from-booking", response_model=ExamAttemptRead, status_code=status.HTTP_201_CREATED)
def start_exam_from_booking(
    payload: ExamStartFromBookingRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("center", "admin", "super_admin")),
) -> ExamAttempt:
    booking = db.scalar(select(Booking).where(Booking.reference == payload.booking_reference))
    if not booking:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found")
    if booking.status not in {"confirmed", "paid", "checked_in"}:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Booking is not eligible for exam start")
    session = db.get(ExamSession, booking.session_id)
    if not session:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Incomplete booking session")
    attempt = _create_exam_attempt(db, booking.candidate_id, booking.session_id)
    _register_exam_start_device(db, attempt, session, payload.device_key, payload.device_label)
    db.commit()
    db.refresh(attempt)
    return attempt


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
    current_user: User = Depends(require_roles("center", "admin", "super_admin")),
) -> ExamAttempt:
    attempt = db.get(ExamAttempt, attempt_id)
    if not attempt:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exam attempt not found")

    now = datetime.utcnow()
    if attempt.status == "submitted":
        _write_exam_guard_log(db, attempt, "exam.replay_submission", "already_submitted", now)
        db.commit()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Exam attempt already submitted")
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

    trace = db.scalar(select(ExamQuestionTrace).where(ExamQuestionTrace.attempt_id == attempt.id))
    if trace and trace.question_ids:
        questions = list(db.scalars(select(Question).where(Question.id.in_(trace.question_ids))).all())
    else:
        questions = list(db.scalars(select(Question).where(Question.is_active.is_(True))).all())
    answer_key = {question.id: question.correct_answer for question in questions}
    result = score_answers(answer_key, payload.answers)

    attempt.answers = payload.answers
    attempt.score = result["correct_answers"]
    attempt.passed = result["passed"]
    attempt.status = "submitted"
    attempt.submitted_at = now
    db.add(attempt)
    db.commit()
    db.refresh(attempt)
    return attempt


@router.get("/{attempt_id}/certificate/verify", response_model=ExamCertificateVerificationRead)
def verify_exam_certificate(attempt_id: str, db: Session = Depends(get_db)) -> ExamCertificateVerificationRead:
    checked_at = datetime.utcnow()
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
        identity_number=candidate.identity_number,
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
    current_user: User = Depends(get_current_user),
) -> Response:
    attempt = db.get(ExamAttempt, attempt_id)
    if not attempt:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exam attempt not found")
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
