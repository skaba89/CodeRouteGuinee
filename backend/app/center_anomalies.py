"""Indicateurs statistiques de surveillance des centres d'examen.

Inspirés du dispositif français de lutte contre la fraude à l'épreuve
théorique (arrêté du 29 avril 2024) : suivi en continu, par centre, du taux de
réussite, de l'éloignement géographique des candidats et des dépassements de
créneau horaire. Un centre signalé fait l'objet d'un contrôle renforcé ; le
signalement est un indicateur, pas une preuve de fraude.

Les seuils sont des paramètres opérationnels, à homologuer par la DNTT.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models_candidate import Candidate
from app.models_center import Center
from app.models_exam_attempt import ExamAttempt
from app.models_session import ExamSession
from app.territory import UNKNOWN_REGION, region_for_prefecture


@dataclass(frozen=True)
class AnomalyThresholds:
    min_exams: int = 20            # volume minimal pour qu'un taux soit interprétable
    pass_rate_z: float = 3.0       # écart au taux national, en écarts-types
    remote_share: float = 0.5      # part de candidats d'une autre région


def detect_center_anomalies(
    db: Session,
    *,
    since: datetime,
    until: datetime | None = None,
    thresholds: AnomalyThresholds = AnomalyThresholds(),
) -> dict:
    settings = get_settings()
    open_before = timedelta(minutes=settings.exam_start_open_minutes_before)
    close_after = timedelta(minutes=settings.exam_start_close_minutes_after)

    period = [ExamAttempt.status == "submitted", ExamAttempt.submitted_at >= since]
    if until is not None:
        period.append(ExamAttempt.submitted_at < until)
    rows = db.execute(
        select(
            ExamSession.center_id,
            ExamSession.starts_at,
            ExamAttempt.started_at,
            ExamAttempt.passed,
            Candidate.city,
        )
        .join(ExamAttempt, ExamAttempt.session_id == ExamSession.id)
        .join(Candidate, Candidate.id == ExamAttempt.candidate_id)
        .where(*period)
    ).all()

    stats: dict[str, dict] = {}
    for center_id, starts_at, started_at, passed, city in rows:
        row = stats.setdefault(center_id, {"exams": 0, "passed": 0, "located": 0, "remote": 0, "off_slot": 0, "cities": []})
        row["exams"] += 1
        row["passed"] += int(bool(passed))
        if started_at < starts_at - open_before or started_at > starts_at + close_after:
            row["off_slot"] += 1
        row["cities"].append(city)

    total_exams = sum(row["exams"] for row in stats.values())
    national_rate = sum(row["passed"] for row in stats.values()) / total_exams if total_exams else None

    centers = {c.id: c for c in db.scalars(select(Center).where(Center.id.in_(list(stats)))).all()}
    flagged = []
    for center_id, row in stats.items():
        center = centers.get(center_id)
        if center is None:
            continue
        center_region = region_for_prefecture(center.prefecture)
        for city in row.pop("cities"):
            candidate_region = region_for_prefecture(city)
            if candidate_region == UNKNOWN_REGION or center_region == UNKNOWN_REGION:
                continue
            row["located"] += 1
            row["remote"] += int(candidate_region != center_region)

        alerts = []
        rate = row["passed"] / row["exams"]
        z_score = None
        if national_rate is not None and 0 < national_rate < 1 and row["exams"] >= thresholds.min_exams:
            z_score = (rate - national_rate) / math.sqrt(national_rate * (1 - national_rate) / row["exams"])
            if z_score >= thresholds.pass_rate_z:
                alerts.append({
                    "code": "PASS_RATE_OUTLIER",
                    "label": "Taux de réussite anormalement élevé",
                    "detail": f"{rate:.0%} contre {national_rate:.0%} au national sur {row['exams']} examens",
                })
        remote_share = row["remote"] / row["located"] if row["located"] else None
        if remote_share is not None and row["located"] >= thresholds.min_exams and remote_share >= thresholds.remote_share:
            alerts.append({
                "code": "REMOTE_CANDIDATES",
                "label": "Candidats venus d'autres régions",
                "detail": f"{remote_share:.0%} des candidats résident hors de la région {center_region}",
            })
        if row["off_slot"]:
            alerts.append({
                "code": "OFF_SLOT_ATTEMPTS",
                "label": "Examens démarrés hors créneau",
                "detail": f"{row['off_slot']} examen(s) démarré(s) hors de la fenêtre autorisée",
            })
        if not alerts:
            continue
        flagged.append({
            "center_id": center.id,
            "code": center.code,
            "name": center.name,
            "region": center_region,
            "exams": row["exams"],
            "pass_rate_pct": round(rate * 100, 1),
            "z_score": round(z_score, 2) if z_score is not None else None,
            "remote_share_pct": round(remote_share * 100, 1) if remote_share is not None else None,
            "off_slot_attempts": row["off_slot"],
            "alerts": alerts,
        })

    flagged.sort(key=lambda item: (len(item["alerts"]), item["z_score"] or 0), reverse=True)
    return {
        "since": since.isoformat(),
        "national": {
            "exams": total_exams,
            "pass_rate_pct": round(national_rate * 100, 1) if national_rate is not None else None,
        },
        "thresholds": {
            "min_exams": thresholds.min_exams,
            "pass_rate_z": thresholds.pass_rate_z,
            "remote_share_pct": round(thresholds.remote_share * 100),
        },
        "centers": flagged,
    }
