from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.exam_engine import score_answers
from app.models_exam_attempt import ExamAttempt
from app.models_question import Question
from app.schemas import ExamAttemptRead, ExamStartRequest, ExamSubmitRequest

router = APIRouter(prefix="/exams", tags=["exams"])


@router.post("/start", response_model=ExamAttemptRead, status_code=status.HTTP_201_CREATED)
def start_exam(payload: ExamStartRequest, db: Session = Depends(get_db)) -> ExamAttempt:
    attempt = ExamAttempt(candidate_id=payload.candidate_id, session_id=payload.session_id)
    db.add(attempt)
    db.commit()
    db.refresh(attempt)
    return attempt


@router.post("/{attempt_id}/submit", response_model=ExamAttemptRead)
def submit_exam(attempt_id: str, payload: ExamSubmitRequest, db: Session = Depends(get_db)) -> ExamAttempt:
    attempt = db.get(ExamAttempt, attempt_id)
    if not attempt:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exam attempt not found")
    if attempt.status == "submitted":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Exam attempt already submitted")

    questions = db.scalars(select(Question).where(Question.is_active.is_(True))).all()
    answer_key = {question.id: question.correct_answer for question in questions}
    result = score_answers(answer_key, payload.answers)

    attempt.answers = payload.answers
    attempt.score = result["correct_answers"]
    attempt.passed = result["passed"]
    attempt.status = "submitted"
    attempt.submitted_at = datetime.utcnow()
    db.add(attempt)
    db.commit()
    db.refresh(attempt)
    return attempt
