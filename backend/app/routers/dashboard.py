from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models_candidate import Candidate
from app.models_center import Center
from app.models_question import Question
from app.models_session import ExamSession
from app.schemas import DashboardRead

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


def _build_dashboard(db: Session) -> DashboardRead:
    return DashboardRead(
        candidates=db.query(Candidate).count(),
        accredited_centers=db.query(Center).filter(Center.status == "active").count(),
        exam_sessions=db.query(ExamSession).count(),
        questions=db.query(Question).count(),
        fraud_alerts=0,
    )


@router.get("", response_model=DashboardRead)
def dashboard(db: Session = Depends(get_db)) -> DashboardRead:
    return _build_dashboard(db)


@router.get("/export.csv")
def export_dashboard_csv(db: Session = Depends(get_db)) -> Response:
    data = _build_dashboard(db)
    rows = [
        "metric,value",
        f"candidates,{data.candidates}",
        f"accredited_centers,{data.accredited_centers}",
        f"exam_sessions,{data.exam_sessions}",
        f"questions,{data.questions}",
        f"fraud_alerts,{data.fraud_alerts}",
    ]
    csv_content = "\n".join(rows) + "\n"
    headers = {"Content-Disposition": "attachment; filename=coderoute-dashboard-export.csv"}
    return Response(content=csv_content, media_type="text/csv", headers=headers)
