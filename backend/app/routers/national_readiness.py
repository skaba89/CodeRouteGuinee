"""Readiness nationale v2 — preuves opérationnelles pour un déploiement public.

Ce module ne remplace pas les dashboards métier. Il fournit une lecture plus
stricte, conçue pour un comité de pilotage / homologation : un pilier n'est
considéré prêt que lorsqu'une preuve mesurable existe dans la plateforme.
"""
from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.deps import require_roles
from app.exam_engine import CATEGORY_DISTRIBUTION, EXAM_QUESTIONS_TOTAL, filter_official_exam_pool
from app.models_audit import AuditLog
from app.models_center import Center
from app.models_center_incident import CenterIncident
from app.models_center_station import CenterStation
from app.models_device_session import DeviceSession
from app.models_exam_attempt import ExamAttempt
from app.models_exam_question_trace import ExamQuestionTrace
from app.models_question import Question
from app.models_session import ExamSession
from app.models_user import User
from app.national_media_readiness import build_national_media_readiness, national_media_strict_ready

router = APIRouter(prefix="/national-readiness", tags=["national-readiness"])


def _pct(numerator: int, denominator: int) -> float:
    return round((numerator / denominator) * 100, 1) if denominator else 0.0


def _weighted(points: int, factor: float) -> int:
    return round(points * max(0.0, min(1.0, factor)))


def _group_counts(rows) -> dict[str, int]:
    return {str(key): int(value) for key, value in rows}


@router.get("")
def get_national_readiness(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "super_admin")),
) -> dict:
    now = datetime.now(UTC).replace(tzinfo=None)
    next_7d = now + timedelta(days=7)
    last_24h = now - timedelta(hours=24)

    # ── Banque officielle réellement éligible ────────────────────────────
    approved = list(db.scalars(
        select(Question).where(
            Question.is_active.is_(True),
            Question.validation_status == "approved",
        )
    ).all())
    eligible = filter_official_exam_pool(approved)
    by_category = Counter(question.category for question in eligible)
    category_coverage = {
        category: {
            "required": required,
            "eligible": by_category.get(category, 0),
            "sufficient": by_category.get(category, 0) >= required,
        }
        for category, required in CATEGORY_DISTRIBUTION.items()
    }
    category_factors = [
        min(1.0, item["eligible"] / item["required"])
        for item in category_coverage.values()
        if item["required"]
    ]
    bank_factor = min(
        1.0,
        len(eligible) / EXAM_QUESTIONS_TOTAL if EXAM_QUESTIONS_TOTAL else 0.0,
        min(category_factors) if category_factors else 0.0,
    )
    bank_ready = (
        len(eligible) >= EXAM_QUESTIONS_TOTAL
        and all(item["sufficient"] for item in category_coverage.values())
    )
    media_readiness = build_national_media_readiness(db, eligible)
    strict_media_ready = national_media_strict_ready(media_readiness)
    pilot_compatible = bank_ready and bool(media_readiness["runtime_exam_constructible"])
    national_bank_ready = bank_ready and strict_media_ready

    # ── Centres et postes ─────────────────────────────────────────────────
    centers = list(db.scalars(select(Center).order_by(Center.code)).all())
    operational_centers = [center for center in centers if center.status in {"active", "accredited"}]
    operational_ids = {center.id for center in operational_centers}

    station_counts = _group_counts(db.execute(
        select(CenterStation.center_id, func.count(CenterStation.id))
        .where(CenterStation.status == "active")
        .group_by(CenterStation.center_id)
    ).all())
    centers_with_stations = sum(1 for center_id in operational_ids if station_counts.get(center_id, 0) > 0)

    upcoming_counts = _group_counts(db.execute(
        select(ExamSession.center_id, func.count(ExamSession.id))
        .where(
            ExamSession.starts_at >= now,
            ExamSession.starts_at <= next_7d,
            ExamSession.status.notin_(["closed", "cancelled"]),
        )
        .group_by(ExamSession.center_id)
    ).all())
    centers_with_upcoming = sum(1 for center_id in operational_ids if upcoming_counts.get(center_id, 0) > 0)

    open_incident_counts = _group_counts(db.execute(
        select(CenterIncident.center_id, func.count(CenterIncident.id))
        .where(CenterIncident.status != "resolved")
        .group_by(CenterIncident.center_id)
    ).all())
    critical_incident_counts = _group_counts(db.execute(
        select(CenterIncident.center_id, func.count(CenterIncident.id))
        .where(
            CenterIncident.status != "resolved",
            CenterIncident.severity.in_(["high", "critical"]),
        )
        .group_by(CenterIncident.center_id)
    ).all())
    critical_open_total = sum(critical_incident_counts.values())

    suspicious_counts = _group_counts(db.execute(
        select(DeviceSession.center_id, func.count(DeviceSession.id))
        .where(
            DeviceSession.status == "suspicious",
            DeviceSession.last_seen_at >= last_24h,
        )
        .group_by(DeviceSession.center_id)
    ).all())
    recent_device_count = int(db.scalar(
        select(func.count()).select_from(DeviceSession).where(DeviceSession.last_seen_at >= last_24h)
    ) or 0)

    # ── Preuve d'intégrité des examens terminés ───────────────────────────
    submitted_attempts = int(db.scalar(
        select(func.count()).select_from(ExamAttempt).where(ExamAttempt.status == "submitted")
    ) or 0)
    traced_submitted = int(db.scalar(
        select(func.count(func.distinct(ExamQuestionTrace.attempt_id)))
        .select_from(ExamQuestionTrace)
        .join(ExamAttempt, ExamAttempt.id == ExamQuestionTrace.attempt_id)
        .where(ExamAttempt.status == "submitted")
    ) or 0)
    trace_coverage_percent = _pct(traced_submitted, submitted_attempts)
    trace_factor = (traced_submitted / submitted_attempts) if submitted_attempts else 0.0

    audit_24h = int(db.scalar(
        select(func.count()).select_from(AuditLog).where(AuditLog.created_at >= last_24h)
    ) or 0)
    audit_total = int(db.scalar(select(func.count()).select_from(AuditLog)) or 0)

    # ── Score national pondéré — 100 points ──────────────────────────────
    # Le score de la banque conserve la mesure de maturité/pilote existante.
    # Le rollout national est, lui, strictement bloqué par national_bank_ready.
    center_factor = (len(operational_centers) / len(centers)) if centers else 0.0
    station_factor = (centers_with_stations / len(operational_centers)) if operational_centers else 0.0
    session_factor = (centers_with_upcoming / len(operational_centers)) if operational_centers else 0.0

    monitoring_factor = 1.0 if centers_with_stations and recent_device_count else (0.4 if centers_with_stations else 0.0)
    incident_factor = 1.0 if critical_open_total == 0 else 0.0
    audit_factor = 1.0 if audit_24h > 0 else (0.4 if audit_total > 0 else 0.0)

    pillars = {
        "official_question_bank": {
            "weight": 25,
            "score": _weighted(25, bank_factor),
            "ready": national_bank_ready,
            "pilot_compatible": pilot_compatible,
            "strict_media_ready": strict_media_ready,
        },
        "operational_centers": {
            "weight": 15,
            "score": _weighted(15, center_factor),
            "ready": bool(centers) and len(operational_centers) == len(centers),
        },
        "registered_exam_stations": {
            "weight": 20,
            "score": _weighted(20, station_factor),
            "ready": bool(operational_centers) and centers_with_stations == len(operational_centers),
        },
        "sessions_next_7_days": {
            "weight": 10,
            "score": _weighted(10, session_factor),
            "ready": bool(operational_centers) and centers_with_upcoming == len(operational_centers),
        },
        "submitted_exam_trace_integrity": {
            "weight": 15,
            "score": _weighted(15, trace_factor),
            "ready": submitted_attempts > 0 and traced_submitted == submitted_attempts,
        },
        "audit_evidence": {
            "weight": 5,
            "score": _weighted(5, audit_factor),
            "ready": audit_24h > 0,
        },
        "incident_control": {
            "weight": 5,
            "score": _weighted(5, incident_factor),
            "ready": critical_open_total == 0,
        },
        "device_monitoring": {
            "weight": 5,
            "score": _weighted(5, monitoring_factor),
            "ready": centers_with_stations > 0 and recent_device_count > 0,
        },
    }
    score = sum(item["score"] for item in pillars.values())

    blockers: list[str] = []
    if not bank_ready:
        blockers.append("official_question_bank_not_ready")
    if not strict_media_ready:
        blockers.append("official_media_bank_not_strict_ready")
    if not operational_centers:
        blockers.append("no_operational_exam_center")
    if operational_centers and centers_with_stations < len(operational_centers):
        blockers.append("exam_station_provisioning_incomplete")
    if operational_centers and centers_with_upcoming < len(operational_centers):
        blockers.append("upcoming_session_coverage_incomplete")
    if submitted_attempts == 0:
        blockers.append("pilot_exam_evidence_missing")
    elif traced_submitted < submitted_attempts:
        blockers.append("submitted_exam_trace_gap")
    if critical_open_total:
        blockers.append("unresolved_high_severity_center_incidents")
    if audit_total == 0:
        blockers.append("audit_evidence_missing")

    if score >= 90 and not blockers:
        status_label = "national_ready"
    elif score >= 75:
        status_label = "pilot_ready"
    elif score >= 60:
        status_label = "remediation_required"
    else:
        status_label = "not_ready"

    # ── Matrice centre par centre ─────────────────────────────────────────
    center_matrix = []
    for center in centers:
        operational = center.id in operational_ids
        active_stations = station_counts.get(center.id, 0)
        upcoming = upcoming_counts.get(center.id, 0)
        open_incidents = open_incident_counts.get(center.id, 0)
        critical_incidents = critical_incident_counts.get(center.id, 0)
        suspicious = suspicious_counts.get(center.id, 0)

        center_score = 0
        center_blockers: list[str] = []
        if operational:
            center_score += 40
        else:
            center_blockers.append("center_not_operational")
        if active_stations > 0:
            center_score += 30
        else:
            center_blockers.append("no_active_registered_station")
        if upcoming > 0:
            center_score += 15
        else:
            center_blockers.append("no_session_next_7_days")
        if critical_incidents == 0:
            center_score += 10
        else:
            center_blockers.append("high_severity_incident_open")
        if suspicious == 0:
            center_score += 5
        else:
            center_blockers.append("suspicious_device_activity_24h")

        center_matrix.append({
            "center_id": center.id,
            "code": center.code,
            "name": center.name,
            "city": center.city,
            "status": center.status,
            "readiness_score": center_score,
            "ready": center_score >= 80 and operational and active_stations > 0,
            "active_registered_stations": active_stations,
            "upcoming_sessions_7d": upcoming,
            "open_incidents": open_incidents,
            "critical_open_incidents": critical_incidents,
            "suspicious_devices_24h": suspicious,
            "blockers": center_blockers,
        })

    national_rollout_allowed = (
        score >= 90
        and national_bank_ready
        and bool(operational_centers)
        and station_factor >= 0.90
        and submitted_attempts > 0
        and traced_submitted == submitted_attempts
        and critical_open_total == 0
    )

    return {
        "generated_at": now.isoformat(),
        "version": "national-readiness-v2",
        "score": score,
        "status": status_label,
        "national_rollout_allowed": national_rollout_allowed,
        "blockers": blockers,
        "pillars": pillars,
        "official_bank": {
            "approved_active": len(approved),
            "eligible_after_training_exclusion": len(eligible),
            "required": EXAM_QUESTIONS_TOTAL,
            "pedagogical_ready": bank_ready,
            "pilot_compatible": pilot_compatible,
            "national_strict_ready": national_bank_ready,
            "ready": national_bank_ready,
            "category_coverage": category_coverage,
            "media": media_readiness,
        },
        "centers": {
            "total": len(centers),
            "operational": len(operational_centers),
            "with_active_registered_station": centers_with_stations,
            "station_coverage_percent": _pct(centers_with_stations, len(operational_centers)),
            "with_session_next_7_days": centers_with_upcoming,
            "session_coverage_percent": _pct(centers_with_upcoming, len(operational_centers)),
            "matrix": center_matrix,
        },
        "exam_integrity": {
            "submitted_attempts": submitted_attempts,
            "submitted_with_trace": traced_submitted,
            "trace_coverage_percent": trace_coverage_percent,
        },
        "operations": {
            "critical_open_incidents": critical_open_total,
            "recent_device_sessions_24h": recent_device_count,
            "suspicious_devices_24h": sum(suspicious_counts.values()),
            "audit_events_24h": audit_24h,
            "audit_events_total": audit_total,
        },
        "methodology": {
            "score_max": 100,
            "national_ready_threshold": 90,
            "pilot_ready_threshold": 75,
            "note": "Les seuils opérationnels mesurent l'état de préparation technique ; ils ne remplacent pas une homologation formelle DNTT/Ministère.",
        },
    }