from datetime import datetime, timedelta

from pydantic import BaseModel
from fastapi import APIRouter, Depends, Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.deps import require_roles
from app.models_audit import AuditLog
from app.models_candidate import Candidate
from app.models_candidate_identity import CandidateIdentityCheck
from app.models_center import Center
from app.models_center_incident import CenterIncident
from app.models_device_session import DeviceSession
from app.models_exam_monitoring import ExamMonitoringEvent
from app.models_institutional_authorization import InstitutionalAuthorization
from app.models_question import Question
from app.models_question_governance import QuestionGovernanceDecision
from app.models_session import ExamSession
from app.models_user import User
from app.schemas import DashboardRead

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


class AntiFraudCenterRisk(BaseModel):
    center_id: str | None = None
    center_code: str | None = None
    open_incidents: int = 0
    suspicious_devices: int = 0
    monitoring_events: int = 0
    monitoring_risk_score: int = 0
    total_risk_score: int = 0
    status: str = "normal"


class AntiFraudDashboardRead(BaseModel):
    open_center_incidents: int
    suspicious_device_sessions: int
    high_risk_monitoring_events: int
    critical_monitoring_events: int
    total_monitoring_risk_score: int
    manual_review_attempts: int
    centers_at_risk: list[AntiFraudCenterRisk]


class InstitutionalReadinessItem(BaseModel):
    pillar: str
    status: str
    evidence: str
    next_step: str


class InstitutionalReadinessRead(BaseModel):
    score: int
    label: str
    summary: str
    items: list[InstitutionalReadinessItem]


class InstitutionalReportRead(BaseModel):
    generated_for: str
    readiness_score: int
    readiness_label: str
    candidates: int
    centers_by_status: dict[str, int]
    questions_by_status: dict[str, int]
    identity_checks_by_status: dict[str, int]
    authorizations_by_status: dict[str, int]
    audit_events: int
    recommendations: list[str]


class InstitutionalActionItem(BaseModel):
    code: str
    label: str
    count: int
    severity: str
    target: str


class InstitutionalActionCenterRead(BaseModel):
    total_actions: int
    critical_actions: int
    items: list[InstitutionalActionItem]


def _build_dashboard(db: Session) -> DashboardRead:
    fraud_alerts = db.query(CenterIncident).filter(CenterIncident.status == "open").count()
    fraud_alerts += db.query(DeviceSession).filter(DeviceSession.status == "suspicious").count()
    fraud_alerts += db.query(ExamMonitoringEvent).filter(ExamMonitoringEvent.severity.in_(["high", "critical"])).count()
    return DashboardRead(
        candidates=db.query(Candidate).count(),
        accredited_centers=db.query(Center).filter(Center.status.in_(["active", "accredited"])).count(),
        exam_sessions=db.query(ExamSession).count(),
        questions=db.query(Question).count(),
        fraud_alerts=fraud_alerts,
    )


def _build_action_item(code: str, label: str, count: int, target: str, warning: int, critical: int) -> InstitutionalActionItem:
    severity = "critical" if count >= critical else "warning" if count >= warning else "normal"
    return InstitutionalActionItem(code=code, label=label, count=count, severity=severity, target=target)


def _count_by_status(db: Session, model: object, status_column: object) -> dict[str, int]:
    rows = db.execute(select(status_column, func.count()).select_from(model).group_by(status_column)).all()
    return {str(status): int(count) for status, count in rows}


def _risk_status(score: int) -> str:
    if score >= 30:
        return "critical_review"
    if score >= 15:
        return "manual_review"
    if score >= 5:
        return "watch"
    return "normal"


@router.get("", response_model=DashboardRead)
def dashboard(db: Session = Depends(get_db)) -> DashboardRead:
    return _build_dashboard(db)


def _build_action_center(db: Session) -> InstitutionalActionCenterRead:
    soon = datetime.utcnow() + timedelta(days=30)
    pending_identities = db.query(CandidateIdentityCheck).filter(CandidateIdentityCheck.status.in_(["pending", "needs_review"])).count()
    centers_to_review = db.query(Center).filter(Center.status.in_(["pending_audit", "suspended"])).count()
    authorizations_to_sign = db.query(InstitutionalAuthorization).filter(InstitutionalAuthorization.status.in_(["draft", "pending_signature"])).count()
    expiring_authorizations = db.query(InstitutionalAuthorization).filter(
        InstitutionalAuthorization.valid_until.is_not(None),
        InstitutionalAuthorization.valid_until <= soon,
        InstitutionalAuthorization.status.in_(["approved", "pending_signature"]),
    ).count()
    questions_to_review = db.query(QuestionGovernanceDecision).filter(QuestionGovernanceDecision.status == "needs_revision").count()
    open_incidents = db.query(CenterIncident).filter(CenterIncident.status == "open").count()

    items = [
        _build_action_item("identity_checks", "Identites candidates a traiter", pending_identities, "#identites", warning=1, critical=10),
        _build_action_item("center_governance", "Centres a auditer ou suspendus", centers_to_review, "#centres", warning=1, critical=5),
        _build_action_item("authorizations_signature", "Habilitations en attente de signature", authorizations_to_sign, "#habilitations", warning=1, critical=3),
        _build_action_item("authorizations_expiry", "Habilitations proches de l'expiration", expiring_authorizations, "#habilitations", warning=1, critical=3),
        _build_action_item("question_revision", "Questions officielles a relire", questions_to_review, "#questions", warning=1, critical=5),
        _build_action_item("open_incidents", "Incidents centres ouverts", open_incidents, "#audit", warning=1, critical=5),
    ]
    active_items = [item for item in items if item.count > 0]
    return InstitutionalActionCenterRead(
        total_actions=sum(item.count for item in active_items),
        critical_actions=sum(item.count for item in active_items if item.severity == "critical"),
        items=active_items,
    )


def _build_institutional_readiness(db: Session) -> InstitutionalReadinessRead:
    data = _build_dashboard(db)
    audit_count = db.query(AuditLog).count()
    active_centers = data.accredited_centers
    has_question_bank = data.questions >= 40
    has_operational_flow = data.candidates > 0 and data.exam_sessions > 0
    has_audit_trail = audit_count > 0
    has_supervision = data.fraud_alerts >= 0

    items = [
        InstitutionalReadinessItem(
            pillar="Gouvernance nationale",
            status="ready" if active_centers > 0 else "todo",
            evidence=f"{active_centers} centre(s) actif(s) ou accredite(s) suivis dans la plateforme.",
            next_step="Valider la nomenclature officielle des centres agrees avec l'administration.",
        ),
        InstitutionalReadinessItem(
            pillar="Parcours candidat",
            status="ready" if has_operational_flow else "todo",
            evidence=f"{data.candidates} candidat(s) et {data.exam_sessions} session(s) d'examen references.",
            next_step="Connecter l'inscription aux registres administratifs et pieces d'identite.",
        ),
        InstitutionalReadinessItem(
            pillar="Banque nationale de questions",
            status="ready" if has_question_bank else "partial",
            evidence=f"{data.questions} question(s) actives dans la banque.",
            next_step="Constituer une banque officielle par categorie de permis et langue.",
        ),
        InstitutionalReadinessItem(
            pillar="Tracabilite et audit",
            status="ready" if has_audit_trail else "partial",
            evidence=f"{audit_count} evenement(s) d'audit enregistres.",
            next_step="Definir la duree legale de conservation et les profils habilites.",
        ),
        InstitutionalReadinessItem(
            pillar="Securite antifraude",
            status="ready" if has_supervision else "partial",
            evidence=f"{data.fraud_alerts} alerte(s) consolidee(s) dans le tableau national.",
            next_step="Ajouter verification d'identite renforcee, photo et supervision en centre.",
        ),
    ]
    weights = {"ready": 20, "partial": 10, "todo": 0}
    score = sum(weights[item.status] for item in items)
    label = "Pret pour pilote institutionnel" if score >= 80 else "Pilote a renforcer" if score >= 50 else "Socle a completer"
    return InstitutionalReadinessRead(
        score=score,
        label=label,
        summary="Lecture executive pour presenter le niveau de maturite de CodeRoute Guinee a l'Etat guineen.",
        items=items,
    )


def _build_institutional_report(db: Session) -> InstitutionalReportRead:
    readiness = _build_institutional_readiness(db)
    centers_by_status = _count_by_status(db, Center, Center.status)
    identity_checks_by_status = _count_by_status(db, CandidateIdentityCheck, CandidateIdentityCheck.status)
    authorizations_by_status = _count_by_status(db, InstitutionalAuthorization, InstitutionalAuthorization.status)
    question_governance_by_status = _count_by_status(db, QuestionGovernanceDecision, QuestionGovernanceDecision.status)
    active_questions = db.query(Question).filter(Question.is_active.is_(True)).count()
    inactive_questions = db.query(Question).filter(Question.is_active.is_(False)).count()
    questions_by_status = {"active": active_questions, "inactive": inactive_questions, **question_governance_by_status}
    recommendations = [item.next_step for item in readiness.items if item.status != "ready"]
    if not recommendations:
        recommendations = ["Maintenir le controle continu, les audits et la revue periodique du dispositif."]
    return InstitutionalReportRead(
        generated_for="Etat guineen - dossier CodeRoute Guinee",
        readiness_score=readiness.score,
        readiness_label=readiness.label,
        candidates=db.query(Candidate).count(),
        centers_by_status=centers_by_status,
        questions_by_status=questions_by_status,
        identity_checks_by_status=identity_checks_by_status,
        authorizations_by_status=authorizations_by_status,
        audit_events=db.query(AuditLog).count(),
        recommendations=recommendations,
    )


@router.get("/institutional-readiness", response_model=InstitutionalReadinessRead)
def institutional_readiness(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "super_admin")),
) -> InstitutionalReadinessRead:
    readiness = _build_institutional_readiness(db)
    db.add(
        AuditLog(
            actor_id=current_user.id,
            action="dashboard.institutional_readiness_viewed",
            entity="dashboard",
            entity_id="institutional-readiness",
            details={"score": readiness.score, "label": readiness.label},
        )
    )
    db.commit()
    return readiness


@router.get("/institutional-action-center", response_model=InstitutionalActionCenterRead)
def institutional_action_center(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "super_admin")),
) -> InstitutionalActionCenterRead:
    action_center = _build_action_center(db)
    db.add(
        AuditLog(
            actor_id=current_user.id,
            action="dashboard.institutional_action_center_viewed",
            entity="dashboard",
            entity_id="institutional-action-center",
            details={"total_actions": action_center.total_actions, "critical_actions": action_center.critical_actions},
        )
    )
    db.commit()
    return action_center


@router.get("/institutional-report", response_model=InstitutionalReportRead)
def institutional_report(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "super_admin")),
) -> InstitutionalReportRead:
    report = _build_institutional_report(db)
    db.add(
        AuditLog(
            actor_id=current_user.id,
            action="dashboard.institutional_report_viewed",
            entity="dashboard",
            entity_id="institutional-report",
            details={"readiness_score": report.readiness_score, "readiness_label": report.readiness_label},
        )
    )
    db.commit()
    return report


@router.get("/institutional-report.csv")
def export_institutional_report_csv(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "super_admin")),
) -> Response:
    report = _build_institutional_report(db)
    rows = [
        "section;key;value",
        f"summary;generated_for;{report.generated_for}",
        f"summary;readiness_score;{report.readiness_score}",
        f"summary;readiness_label;{report.readiness_label}",
        f"summary;candidates;{report.candidates}",
        f"summary;audit_events;{report.audit_events}",
    ]
    for status_name, count in report.centers_by_status.items():
        rows.append(f"centers;{status_name};{count}")
    for status_name, count in report.questions_by_status.items():
        rows.append(f"questions;{status_name};{count}")
    for status_name, count in report.identity_checks_by_status.items():
        rows.append(f"identity_checks;{status_name};{count}")
    for status_name, count in report.authorizations_by_status.items():
        rows.append(f"authorizations;{status_name};{count}")
    for index, recommendation in enumerate(report.recommendations, start=1):
        rows.append(f"recommendations;{index};{recommendation}")

    db.add(
        AuditLog(
            actor_id=current_user.id,
            action="dashboard.institutional_report_export_csv",
            entity="dashboard",
            entity_id="institutional-report",
            details={"readiness_score": report.readiness_score, "recommendations": len(report.recommendations)},
        )
    )
    db.commit()
    csv_content = "\n".join(rows) + "\n"
    headers = {"Content-Disposition": "attachment; filename=coderoute-institutional-report.csv"}
    return Response(content=csv_content, media_type="text/csv", headers=headers)


@router.get("/anti-fraud", response_model=AntiFraudDashboardRead)
def anti_fraud_dashboard(
    limit: int = 10,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "super_admin")),
) -> AntiFraudDashboardRead:
    open_incidents = db.query(CenterIncident).filter(CenterIncident.status == "open").count()
    suspicious_devices = db.query(DeviceSession).filter(DeviceSession.status == "suspicious").count()
    high_risk_events = db.query(ExamMonitoringEvent).filter(ExamMonitoringEvent.severity == "high").count()
    critical_events = db.query(ExamMonitoringEvent).filter(ExamMonitoringEvent.severity == "critical").count()
    total_monitoring_risk_score = db.scalar(select(func.coalesce(func.sum(ExamMonitoringEvent.risk_score), 0))) or 0

    attempt_scores = db.execute(
        select(
            ExamMonitoringEvent.attempt_id,
            func.coalesce(func.sum(ExamMonitoringEvent.risk_score), 0).label("risk_score"),
        ).group_by(ExamMonitoringEvent.attempt_id)
    ).all()
    manual_review_attempts = sum(1 for _, score in attempt_scores if int(score or 0) >= 10)

    centers = db.query(Center).all()
    center_rows: list[AntiFraudCenterRisk] = []
    for center in centers:
        center_open_incidents = db.query(CenterIncident).filter(
            CenterIncident.center_id == center.id,
            CenterIncident.status == "open",
        ).count()
        center_suspicious_devices = db.query(DeviceSession).filter(
            DeviceSession.center_id == center.id,
            DeviceSession.status == "suspicious",
        ).count()
        center_monitoring_events = db.query(ExamMonitoringEvent).filter(ExamMonitoringEvent.center_id == center.id).count()
        center_monitoring_risk_score = db.scalar(
            select(func.coalesce(func.sum(ExamMonitoringEvent.risk_score), 0)).where(ExamMonitoringEvent.center_id == center.id)
        ) or 0
        total_risk_score = int(center_monitoring_risk_score or 0) + center_open_incidents * 5 + center_suspicious_devices * 4
        if total_risk_score == 0:
            continue
        center_rows.append(
            AntiFraudCenterRisk(
                center_id=center.id,
                center_code=center.code,
                open_incidents=center_open_incidents,
                suspicious_devices=center_suspicious_devices,
                monitoring_events=center_monitoring_events,
                monitoring_risk_score=int(center_monitoring_risk_score or 0),
                total_risk_score=total_risk_score,
                status=_risk_status(total_risk_score),
            )
        )

    center_rows.sort(key=lambda item: item.total_risk_score, reverse=True)
    return AntiFraudDashboardRead(
        open_center_incidents=open_incidents,
        suspicious_device_sessions=suspicious_devices,
        high_risk_monitoring_events=high_risk_events,
        critical_monitoring_events=critical_events,
        total_monitoring_risk_score=int(total_monitoring_risk_score or 0),
        manual_review_attempts=manual_review_attempts,
        centers_at_risk=center_rows[: max(1, min(limit, 50))],
    )


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
