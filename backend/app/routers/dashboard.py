from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.deps import require_roles
from app.models_audit import AuditLog
from app.models_candidate import Candidate
from app.models_center import Center
from app.models_question import Question
from app.models_session import ExamSession
from app.models_user import User
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
def export_dashboard_csv(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "super_admin")),
) -> Response:
    data = _build_dashboard(db)
    audit_log = AuditLog(
        actor_id=current_user.id,
        action="dashboard.export_csv",
        entity="dashboard",
        entity_id="national-dashboard",
        details={
            "format": "csv",
            "metrics": {
                "candidates": data.candidates,
                "accredited_centers": data.accredited_centers,
                "exam_sessions": data.exam_sessions,
                "questions": data.questions,
                "fraud_alerts": data.fraud_alerts,
            },
        },
    )
    db.add(audit_log)
    db.commit()

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
