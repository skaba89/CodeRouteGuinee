from datetime import datetime

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.deps import require_roles
from app.models_session import ExamSession
from app.models_user import User
from app.schemas import ExamSessionCreate, ExamSessionRead

router = APIRouter(prefix="/sessions", tags=["sessions"])


def build_session_reference(db: Session) -> str:
    count = db.query(ExamSession).count() + 1
    return f"GN-SESSION-{datetime.utcnow().year}-{count:06d}"


@router.get("", response_model=list[ExamSessionRead])
def list_sessions(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "super_admin", "center", "candidate")),
) -> list[ExamSession]:
    return list(db.scalars(select(ExamSession).order_by(ExamSession.starts_at.desc())).all())


@router.post("", response_model=ExamSessionRead, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_roles("admin", "super_admin"))])
def create_session(payload: ExamSessionCreate, db: Session = Depends(get_db)) -> ExamSession:
    exam_session = ExamSession(reference=build_session_reference(db), **payload.model_dump())
    db.add(exam_session)
    db.commit()
    db.refresh(exam_session)
    return exam_session
