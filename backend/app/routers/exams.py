from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.exam_engine import score_answers
from app.models_audit import AuditLog
from app.models_candidate import Candidate
from app.models_center import Center
from app.models_exam_attempt import ExamAttempt
from app.models_question import Question
from app.models_session import ExamSession
from app.pdf_service import build_result_certificate_pdf
from app.schemas import ExamAttemptRead, ExamCertificateVerificationRead, ExamStartRequest, ExamSubmitRequest

router = APIRouter(prefix="/exams", tags=["exams"])

EXAM_DURATION_MINUTES = 30


def _is_attempt_expired(attempt: ExamAttempt, now: datetime) -> bool:
    return now - attempt.started_at > timedelta(minutes=EXAM_DURATION_MINUTES)


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


@router.post("/start", response_model=ExamAttemptRead, status_code=status.HTTP_201_CREATED)
def start_exam(payload: ExamStartRequest, db: Session = Depends(get_db)) -> ExamAttempt:
    attempt = ExamAttempt(candidate_id=payload.candidate_id, session_id=payload.session_id)
    db.add(attempt)
    db.commit()
    db.refresh(attempt)
    return attempt


@router.get("/summary")
def get_exam_summary(db: Session = Depends(get_db)) -> dict:
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


@router.post("/{attempt_id}/submit", response_model=ExamAttemptRead)
def submit_exam(attempt_id: str, payload: ExamSubmitRequest, db: Session = Depends(get_db)) -> ExamAttempt:
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

    questions = db.scalars(select(Question).where(Question.is_active.is_(True))).all()
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
    attempt = db.get(ExamAttempt, attempt_id)
    if not attempt:
        return ExamCertificateVerificationRead(
            valid=False,
            attempt_id=attempt_id,
            status="not_found",
            reason="Tentative d'examen introuvable",
        )
    if attempt.status != "submitted":
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
        return ExamCertificateVerificationRead(
            valid=False,
            attempt_id=attempt.id,
            status="incomplete",
            reason="Donnees du certificat incompletes",
        )

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
def get_exam_certificate(attempt_id: str, db: Session = Depends(get_db)) -> Response:
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
