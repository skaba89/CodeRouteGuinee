from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.deps import require_roles
from app.models_audit import AuditLog
from app.models_booking import Booking
from app.models_candidate import Candidate
from app.models_candidate_identity import CandidateIdentityCheck
from app.models_center import Center
from app.models_center_incident import CenterIncident
from app.models_device_session import DeviceSession
from app.models_exam_monitoring import ExamMonitoringEvent
from app.models_institutional_authorization import InstitutionalAuthorization
from app.models_payment import Payment
from app.models_question import Question
from app.models_question_governance import QuestionGovernanceDecision
from app.models_session import ExamSession
from app.models_user import User
from app.pdf_service import build_institutional_report_pdf
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
    from datetime import UTC, datetime, timedelta

    from app.models_booking import Booking
    from app.models_exam_attempt import ExamAttempt
    from app.models_payment import Payment

    fraud_alerts = (db.scalar(select(func.count(CenterIncident.id)).where(CenterIncident.status == "open")) or 0)
    fraud_alerts += (db.scalar(select(func.count(DeviceSession.id)).where(DeviceSession.status == "suspicious")) or 0)
    fraud_alerts += (db.scalar(select(func.count(ExamMonitoringEvent.id)).where(ExamMonitoringEvent.severity.in_(["high", "critical"]))) or 0)

    # KPIs examens
    passed = (db.scalar(select(func.count(ExamAttempt.id)).where(ExamAttempt.passed.is_(True))) or 0)
    failed = (db.scalar(select(func.count(ExamAttempt.id)).where(ExamAttempt.passed.is_(False))) or 0)
    total_attempts = passed + failed
    pass_rate = round(passed / total_attempts * 100, 1) if total_attempts > 0 else 0.0

    # KPIs financiers
    payments_total = (db.scalar(select(func.count(Payment.id)).where(Payment.status == "paid")) or 0)
    revenue_row = db.execute(
        select(func.coalesce(func.sum(Payment.amount_gnf), 0))
        .where(Payment.status == "paid")
    ).scalar()
    revenue_gnf = int(revenue_row or 0)

    # Sessions de la semaine
    now = datetime.now(UTC).replace(tzinfo=None)
    week_start = now - timedelta(days=now.weekday())
    week_end   = week_start + timedelta(days=7)
    sessions_week = (db.scalar(select(func.count(ExamSession.id)).where(
        ExamSession.starts_at >= week_start,
        ExamSession.starts_at < week_end,
    )) or 0)
    sessions_available = (db.scalar(select(func.count(ExamSession.id)).where(
        ExamSession.status == "open",
        ExamSession.starts_at > now,
    )) or 0)

    # Réservations en attente
    bookings_pending = (db.scalar(select(func.count(Booking.id)).where(Booking.status == "confirmed")) or 0)

    return DashboardRead(
        candidates=(db.scalar(select(func.count(Candidate.id))) or 0),
        accredited_centers=(db.scalar(select(func.count(Center.id)).where(Center.status.in_(["active", "accredited"]))) or 0),
        exam_sessions=(db.scalar(select(func.count(ExamSession.id))) or 0),
        questions=(db.scalar(select(func.count(Question.id))) or 0),
        fraud_alerts=fraud_alerts,
        candidates_passed=passed,
        candidates_failed=failed,
        pass_rate_pct=pass_rate,
        payments_total=payments_total,
        revenue_gnf=revenue_gnf,
        sessions_this_week=sessions_week,
        sessions_available=sessions_available,
        bookings_pending=bookings_pending,
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
def dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "super_admin", "center")),
) -> DashboardRead:
    return _build_dashboard(db)


def _build_action_center(db: Session) -> InstitutionalActionCenterRead:
    soon = datetime.now(UTC).replace(tzinfo=None) + timedelta(days=30)
    pending_identities = (db.scalar(select(func.count(CandidateIdentityCheck.id)).where(CandidateIdentityCheck.status.in_(["pending", "needs_review"]))) or 0)
    centers_to_review = (db.scalar(select(func.count(Center.id)).where(Center.status.in_(["pending_audit", "suspended"]))) or 0)
    authorizations_to_sign = (db.scalar(select(func.count(InstitutionalAuthorization.id)).where(InstitutionalAuthorization.status.in_(["draft", "pending_signature"]))) or 0)
    expiring_authorizations = (db.scalar(select(func.count(InstitutionalAuthorization.id)).where(
        InstitutionalAuthorization.valid_until.isnot(None),
        InstitutionalAuthorization.valid_until <= soon,
        InstitutionalAuthorization.status.in_(["approved", "pending_signature"]),
    )) or 0)
    questions_to_review = (db.scalar(select(func.count(QuestionGovernanceDecision.id)).where(QuestionGovernanceDecision.status == "needs_revision")) or 0)
    open_incidents = (db.scalar(select(func.count(CenterIncident.id)).where(CenterIncident.status == "open")) or 0)

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
    audit_count = (db.scalar(select(func.count(AuditLog.id))) or 0)
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
    active_questions = (db.scalar(select(func.count(Question.id)).where(Question.is_active.is_(True))) or 0)
    inactive_questions = (db.scalar(select(func.count(Question.id)).where(Question.is_active.is_(False))) or 0)
    questions_by_status = {"active": active_questions, "inactive": inactive_questions, **question_governance_by_status}
    recommendations = [item.next_step for item in readiness.items if item.status != "ready"]
    if not recommendations:
        recommendations = ["Maintenir le controle continu, les audits et la revue periodique du dispositif."]
    return InstitutionalReportRead(
        generated_for="Etat guineen - dossier CodeRoute Guinee",
        readiness_score=readiness.score,
        readiness_label=readiness.label,
        candidates=(db.scalar(select(func.count(Candidate.id))) or 0),
        centers_by_status=centers_by_status,
        questions_by_status=questions_by_status,
        identity_checks_by_status=identity_checks_by_status,
        authorizations_by_status=authorizations_by_status,
        audit_events=(db.scalar(select(func.count(AuditLog.id))) or 0),
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


@router.get("/institutional-report.pdf")
def export_institutional_report_pdf(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "super_admin")),
) -> Response:
    report = _build_institutional_report(db)
    db.add(
        AuditLog(
            actor_id=current_user.id,
            action="dashboard.institutional_report_export_pdf",
            entity="dashboard",
            entity_id="institutional-report",
            details={"readiness_score": report.readiness_score, "recommendations": len(report.recommendations)},
        )
    )
    db.commit()
    headers = {"Content-Disposition": "attachment; filename=coderoute-institutional-report.pdf"}
    return Response(content=build_institutional_report_pdf(report.model_dump()), media_type="application/pdf", headers=headers)


@router.get("/anti-fraud", response_model=AntiFraudDashboardRead)
def anti_fraud_dashboard(
    limit: int = 200,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "super_admin")),
) -> AntiFraudDashboardRead:
    open_incidents = (db.scalar(select(func.count(CenterIncident.id)).where(CenterIncident.status == "open")) or 0)
    suspicious_devices = (db.scalar(select(func.count(DeviceSession.id)).where(DeviceSession.status == "suspicious")) or 0)
    high_risk_events = (db.scalar(select(func.count(ExamMonitoringEvent.id)).where(ExamMonitoringEvent.severity == "high")) or 0)
    critical_events = (db.scalar(select(func.count(ExamMonitoringEvent.id)).where(ExamMonitoringEvent.severity == "critical")) or 0)
    total_monitoring_risk_score = db.scalar(select(func.coalesce(func.sum(ExamMonitoringEvent.risk_score), 0))) or 0

    # Compté directement en SQL (HAVING) — évite de matérialiser
    # des dizaines de milliers de lignes attempt_id à l'échelle nationale
    manual_review_attempts = db.scalar(
        select(func.count()).select_from(
            select(ExamMonitoringEvent.attempt_id)
            .group_by(ExamMonitoringEvent.attempt_id)
            .having(func.coalesce(func.sum(ExamMonitoringEvent.risk_score), 0) >= 10)
            .subquery()
        )
    ) or 0

    centers = db.scalars(select(Center)).all()
    center_rows: list[AntiFraudCenterRisk] = []
    for center in centers:
        center_open_incidents = (db.scalar(select(func.count(CenterIncident.id)).where(
            CenterIncident.center_id == center.id,
            CenterIncident.status == "open",
        )) or 0)
        center_suspicious_devices = (db.scalar(select(func.count(DeviceSession.id)).where(
            DeviceSession.center_id == center.id,
            DeviceSession.status == "suspicious",
        )) or 0)
        center_monitoring_events = (db.scalar(select(func.count(ExamMonitoringEvent.id)).where(ExamMonitoringEvent.center_id == center.id)) or 0)
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
        centers_at_risk=center_rows[:limit],
    )




@router.get("/live", tags=["dashboard"])
def get_live_kpis(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "super_admin", "center")),
) -> dict:
    """
    KPIs en temps réel — conçu pour être pollé toutes les 15–30s.
    Retourne les métriques fraîches sans cache.
    Feed d'activité récente des 15 dernières minutes.
    """
    now       = datetime.now(UTC).replace(tzinfo=None)
    last_7d   = now - timedelta(days=7)
    last_15m  = now - timedelta(minutes=15)

    # ── KPIs calculés live ─────────────────────────────────────────────────
    total_candidates   = (db.scalar(select(func.count(Candidate.id))) or 0)
    bookings_today     = (db.scalar(select(func.count(Booking.id)).where(Booking.created_at >= now.replace(hour=0, minute=0, second=0))) or 0)
    bookings_week      = (db.scalar(select(func.count(Booking.id)).where(Booking.created_at >= last_7d)) or 0)
    pending_payments   = (db.scalar(select(func.count(Payment.id)).where(Payment.status == "pending")) or 0)
    paid_today         = (db.scalar(select(func.count(Payment.id)).where(
        Payment.status == "paid",
        Payment.created_at >= now.replace(hour=0, minute=0, second=0, microsecond=0)
    )) or 0)
    active_sessions    = (db.scalar(select(func.count(ExamSession.id)).where(
        ExamSession.status == "open",
        ExamSession.starts_at >= now,
    )) or 0)
    confirmed_bookings = (db.scalar(select(func.count(Booking.id)).where(Booking.status == "confirmed")) or 0)
    open_incidents     = (db.scalar(select(func.count(CenterIncident.id)).where(CenterIncident.status == "open")) or 0)         if hasattr(CenterIncident, "status") else 0
    fraud_active       = 0

    # ── Feed d'activité récente (15 dernières minutes) ─────────────────────
    feed: list[dict] = []

    # Réservations récentes
    recent_bookings = db.scalars(select(Booking).where(
        Booking.created_at >= last_15m
    ).order_by(Booking.created_at.desc()).limit(5)).all()
    for bk in recent_bookings:
        feed.append({
            "id":        str(bk.id),
            "type":      "booking",
            "title":     f"Nouvelle réservation — {bk.reference}",
            "status":    bk.status,
            "timestamp": bk.created_at.isoformat() if bk.created_at else None,
        })

    # Paiements récents
    recent_payments = db.scalars(select(Payment).where(
        Payment.created_at >= last_15m
    ).order_by(Payment.created_at.desc()).limit(5)).all()
    for pay in recent_payments:
        feed.append({
            "id":        str(pay.id) if pay.id else pay.reference,
            "type":      "payment",
            "title":     f"Paiement {pay.status} — {pay.reference} ({pay.amount_gnf:,} GNF)",
            "status":    pay.status,
            "timestamp": pay.created_at.isoformat() if pay.created_at else None,
        })

    # Trier par timestamp
    feed.sort(key=lambda x: x.get("timestamp") or "", reverse=True)

    return {
        "timestamp": now.isoformat(),
        "kpis": {
            "total_candidates":    total_candidates,
            "bookings_today":      bookings_today,
            "bookings_week":       bookings_week,
            "pending_payments":    pending_payments,
            "paid_today":          paid_today,
            "active_sessions":     active_sessions,
            "confirmed_bookings":  confirmed_bookings,
            "open_incidents":      open_incidents,
            "fraud_active":        fraud_active,
        },
        "feed":     feed[:10],
        "poll_interval_seconds": 15,
    }


@router.post("/notifications/run-job", tags=["notifications"])
def run_notification_job(
    job: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "super_admin")),
) -> dict:
    """
    Déclenche manuellement un job de notification.
    Jobs disponibles : exam_reminder_24h, exam_reminder_2h, payment_pending_7d
    """
    from app.scheduled_notifications import JOBS, run_job
    if job not in JOBS:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=400,
            detail=f"Job inconnu : {job}. Disponibles : {list(JOBS.keys())}"
        )
    result = run_job(job)
    return result.to_dict()


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
