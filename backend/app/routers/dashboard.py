from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models_candidate import Candidate
from app.models_center import Center
from app.models_question import Question
from app.models_session import ExamSession
from app.schemas import DashboardRead

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("", response_model=DashboardRead)
def dashboard(db: Session = Depends(get_db)) -> DashboardRead:
    return DashboardRead(
        candidates=db.query(Candidate).count(),
        accredited_centers=db.query(Center).filter(Center.status == "active").count(),
        exam_sessions=db.query(ExamSession).count(),
        questions=db.query(Question).count(),
        fraud_alerts=0,
    )
