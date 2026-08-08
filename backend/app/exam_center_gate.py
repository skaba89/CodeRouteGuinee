"""Contrôles d'accès physique pour les examens officiels CodeRoute.

Ce module sépare clairement :
- la logique métier d'examen (sélection, score, trace) ;
- le contrôle d'accès au centre (heure, centre, paiement, poste enrôlé).

Les fenêtres horaires sont des paramètres opérationnels configurables et ne sont
pas présentées comme des règles juridiques DNTT tant qu'elles ne sont pas
formellement homologuées.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models_center import Center
from app.models_center_station import CenterStation
from app.models_session import ExamSession
from app.models_user import User


@dataclass(frozen=True)
class CenterWindow:
    opens_at: datetime
    starts_at: datetime
    closes_at: datetime
    now: datetime

    @property
    def allowed(self) -> bool:
        return self.opens_at <= self.now <= self.closes_at


def utc_naive(value: datetime) -> datetime:
    """Normalise un datetime SQLAlchemy en UTC naïf, format utilisé en base."""
    if value.tzinfo is None:
        return value
    return value.astimezone(UTC).replace(tzinfo=None)


def now_utc_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _window(
    session: ExamSession,
    *,
    before_minutes: int,
    after_minutes: int,
    now: datetime | None = None,
) -> CenterWindow:
    starts_at = utc_naive(session.starts_at)
    current = utc_naive(now) if now else now_utc_naive()
    return CenterWindow(
        opens_at=starts_at - timedelta(minutes=max(0, before_minutes)),
        starts_at=starts_at,
        closes_at=starts_at + timedelta(minutes=max(0, after_minutes)),
        now=current,
    )


def _window_error(code: str, message: str, window: CenterWindow) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail={
            "code": code,
            "message": message,
            "opens_at": window.opens_at.isoformat(),
            "session_starts_at": window.starts_at.isoformat(),
            "closes_at": window.closes_at.isoformat(),
            "server_time": window.now.isoformat(),
        },
    )


def assert_checkin_window(session: ExamSession, now: datetime | None = None) -> CenterWindow:
    settings = get_settings()
    window = _window(
        session,
        before_minutes=settings.exam_checkin_open_minutes_before,
        after_minutes=settings.exam_checkin_close_minutes_after,
        now=now,
    )
    if not window.allowed:
        raise _window_error(
            "CHECKIN_OUTSIDE_SESSION_WINDOW",
            "Le contrôle d'entrée n'est pas ouvert pour cette session.",
            window,
        )
    return window


def assert_exam_start_window(session: ExamSession, now: datetime | None = None) -> CenterWindow:
    settings = get_settings()
    window = _window(
        session,
        before_minutes=settings.exam_start_open_minutes_before,
        after_minutes=settings.exam_start_close_minutes_after,
        now=now,
    )
    if not window.allowed:
        raise _window_error(
            "EXAM_START_OUTSIDE_SESSION_WINDOW",
            "Le démarrage de l'examen n'est pas ouvert pour cette session.",
            window,
        )
    return window


def require_operational_center(db: Session, session: ExamSession) -> Center:
    center = db.get(Center, session.center_id)
    if not center:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "EXAM_CENTER_NOT_FOUND", "message": "Centre d'examen introuvable."},
        )
    if center.status not in {"active", "accredited"}:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "EXAM_CENTER_NOT_OPERATIONAL",
                "message": "Ce centre n'est pas autorisé à faire passer des examens actuellement.",
                "center_id": center.id,
                "center_status": center.status,
            },
        )
    return center


def assert_center_actor_scope(current_user: User, session: ExamSession) -> None:
    """Un agent centre ne peut agir que sur le centre auquel il est affecté."""
    if current_user.role != "center":
        return
    if current_user.center_id and current_user.center_id == session.center_id:
        return
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail={
            "code": "CENTER_SCOPE_MISMATCH",
            "message": "Cette session appartient à un autre centre.",
        },
    )


def assert_station_allowed(
    db: Session,
    session: ExamSession,
    device_key: str | None,
) -> dict:
    """Contrôle progressif du poste d'examen.

    Tant qu'aucun poste n'est enregistré pour un centre, le pilote continue et
    le retour `enforced=False` permet à la supervision de signaler le centre à
    provisionner. Dès qu'un premier poste existe, le registre devient strict :
    le device_key est obligatoire et doit correspondre à un poste `active`.
    """
    registry_exists = db.scalar(
        select(CenterStation.id)
        .where(CenterStation.center_id == session.center_id)
        .limit(1)
    )
    if not registry_exists:
        return {
            "enforced": False,
            "registered": False,
            "station_id": None,
            "reason": "station_registry_not_configured",
        }

    normalized = (device_key or "").strip()
    if not normalized:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "EXAM_STATION_REQUIRED",
                "message": "Cette session exige un poste d'examen pré-enregistré.",
            },
        )

    station = db.scalar(
        select(CenterStation).where(
            CenterStation.center_id == session.center_id,
            CenterStation.device_key == normalized,
        )
    )
    if not station:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "UNREGISTERED_EXAM_STATION",
                "message": "Ce poste n'est pas enregistré dans ce centre d'examen.",
                "device_key": normalized,
            },
        )
    if station.status != "active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "INACTIVE_EXAM_STATION",
                "message": "Ce poste d'examen est désactivé ou en maintenance.",
                "station_id": station.id,
                "station_status": station.status,
            },
        )

    return {
        "enforced": True,
        "registered": True,
        "station_id": station.id,
        "reason": None,
    }
