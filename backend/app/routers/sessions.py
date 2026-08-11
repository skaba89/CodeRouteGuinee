"""Gestion des sessions d'examen et invariants opérationnels.

Les plafonds 35 candidats / 3 sessions hebdomadaires / fenêtre de 2h sont les
paramètres opérationnels courants de la plateforme. Ils ne sont pas présentés
ici comme une homologation institutionnelle définitive.
"""
from __future__ import annotations

from collections import Counter
from datetime import UTC, date, datetime, time, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.deps import get_current_user, require_roles
from app.models_audit import AuditLog
from app.models_booking import Booking
from app.models_center import Center
from app.models_session import ExamSession
from app.models_user import User
from app.resource_access import assert_center_access, assert_session_access
from app.schemas import ExamSessionCreate, ExamSessionRead
from app.session_rules import (
    MAX_CAPACITY,
    MAX_SESSIONS_PER_WEEK,
    SESSION_DURATION_HOURS,
    acquire_session_reference_lock,
    count_sessions_this_week,
    has_overlapping_session,
    lock_operational_center,
    validate_session_slot,
)

router = APIRouter(prefix="/sessions", tags=["sessions"])


def build_session_reference(db: Session) -> str:
    count = (db.scalar(select(func.count(ExamSession.id))) or 0) + 1
    return f"GN-SESSION-{datetime.now(UTC).year}-{count:06d}"


# Compatibilité des tests/modules historiques qui importaient ces helpers.
def _count_sessions_this_week(db: Session, center_id: str, starts_at: datetime) -> int:
    return count_sessions_this_week(db, center_id, starts_at)


def _has_overlapping_session(
    db: Session,
    center_id: str,
    starts_at: datetime,
    exclude_id: str | None = None,
) -> bool:
    return has_overlapping_session(db, center_id, starts_at, exclude_id)


def _center_scope_query(query, current_user: User):
    if current_user.role == "center":
        if not current_user.center_id:
            return query.where(ExamSession.id == "__no_center__")
        return query.where(ExamSession.center_id == current_user.center_id)
    return query


@router.get("", response_model=dict)
def list_sessions(
    center_id: str | None = Query(default=None),
    commune: str | None = Query(default=None, description="Filtrer par commune"),
    prefecture: str | None = Query(default=None, description="Filtrer par préfecture"),
    week_offset: int | None = Query(default=None, description="0 = cette semaine, 1 = semaine prochaine"),
    session_status: str | None = Query(default=None, alias="status"),
    search: str | None = Query(default=None, description="Recherche sur ID/référence"),
    limit: int = Query(default=20, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    query = select(ExamSession).order_by(ExamSession.starts_at.asc())
    query = _center_scope_query(query, current_user)
    if current_user.role != "center" and center_id:
        query = query.where(ExamSession.center_id == center_id)

    if commune or prefecture:
        query = query.join(Center, ExamSession.center_id == Center.id)
        if commune:
            query = query.where(Center.commune == commune)
        if prefecture:
            query = query.where(Center.prefecture == prefecture)

    if week_offset is not None:
        now = datetime.now(UTC).replace(tzinfo=None)
        week_start = now - timedelta(days=now.weekday()) + timedelta(weeks=week_offset)
        week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)
        week_end = week_start + timedelta(days=7)
        query = query.where(ExamSession.starts_at >= week_start, ExamSession.starts_at < week_end)

    if session_status:
        query = query.where(ExamSession.status == session_status)
    if search:
        term = f"%{search.strip()}%"
        query = query.where(
            (ExamSession.id.ilike(term)) | (ExamSession.reference.ilike(term))
        )

    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    raw_items = list(db.scalars(query.offset(offset).limit(limit)).all())
    items = [ExamSessionRead.model_validate(item) for item in raw_items]
    return {"items": items, "total": total, "limit": limit, "offset": offset, "search": search}


@router.get("/available", response_model=list[ExamSessionRead])
def list_available_sessions(
    commune: str | None = Query(default=None),
    prefecture: str | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[ExamSession]:
    """Sessions futures réservable dans des centres opérationnels uniquement."""
    now = datetime.now(UTC).replace(tzinfo=None)
    query = (
        select(ExamSession)
        .join(Center, ExamSession.center_id == Center.id)
        .where(
            ExamSession.starts_at > now,
            ExamSession.status.in_(["planned", "open"]),
            Center.status.in_(["active", "accredited"]),
        )
        .order_by(ExamSession.starts_at.asc())
    )
    if commune:
        query = query.where(Center.commune == commune)
    if prefecture:
        query = query.where(Center.prefecture == prefecture)

    sessions = list(db.scalars(query).all())
    if not sessions:
        return []
    session_ids = [item.id for item in sessions]
    counts = dict(
        db.execute(
            select(Booking.session_id, func.count(Booking.id))
            .where(Booking.session_id.in_(session_ids), Booking.status.not_in(["cancelled"]))
            .group_by(Booking.session_id)
        ).all()
    )
    return [item for item in sessions if counts.get(item.id, 0) < item.capacity]


@router.get("/week-schedule", response_model=dict)
def get_week_schedule(
    week_offset: int = Query(default=0),
    prefecture: str | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    now = datetime.now(UTC).replace(tzinfo=None)
    week_start = now - timedelta(days=now.weekday()) + timedelta(weeks=week_offset)
    week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)
    week_end = week_start + timedelta(days=7)

    query = (
        select(ExamSession, Center)
        .join(Center, ExamSession.center_id == Center.id)
        .where(
            ExamSession.starts_at >= week_start,
            ExamSession.starts_at < week_end,
            ExamSession.status.not_in(["cancelled", "archived"]),
        )
        .order_by(ExamSession.starts_at.asc())
    )
    if current_user.role == "center":
        if not current_user.center_id:
            query = query.where(ExamSession.id == "__no_center__")
        else:
            query = query.where(ExamSession.center_id == current_user.center_id)
    if prefecture:
        query = query.where(Center.prefecture == prefecture)

    rows = db.execute(query).all()
    days: dict[int, list[dict]] = {index: [] for index in range(7)}
    simultaneous_counter: Counter[datetime] = Counter()
    for session, center in rows:
        simultaneous_counter[session.starts_at] += 1
        days[session.starts_at.weekday()].append(
            {
                "session_id": session.id,
                "reference": session.reference,
                "center_id": center.id,
                "center_name": center.name,
                "commune": center.commune,
                "prefecture": center.prefecture,
                "starts_at": session.starts_at.isoformat(),
                "capacity": session.capacity,
                "status": session.status,
            }
        )

    day_names = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]
    return {
        "week_start": week_start.isoformat(),
        "week_end": week_end.isoformat(),
        "total_sessions": sum(len(items) for items in days.values()),
        "simultaneous_peak": max(simultaneous_counter.values(), default=0),
        "days": {
            day_names[index]: {
                "date": (week_start + timedelta(days=index)).date().isoformat(),
                "sessions": items,
                "centers_count": len({item["center_id"] for item in items}),
            }
            for index, items in days.items()
        },
    }


@router.get("/{session_id}", response_model=ExamSessionRead)
def get_session(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "super_admin", "center")),
) -> ExamSession:
    session = db.get(ExamSession, session_id)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session introuvable")
    assert_session_access(current_user, session)
    return session


@router.get("/{session_id}/capacity-status", response_model=dict)
def get_session_capacity(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    session = db.get(ExamSession, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session introuvable")
    if current_user.role == "center":
        assert_session_access(current_user, session)

    booked = db.scalar(
        select(func.count(Booking.id)).where(
            Booking.session_id == session_id,
            Booking.status.not_in(["cancelled"]),
        )
    ) or 0
    return {
        "session_id": session_id,
        "reference": session.reference,
        "capacity": session.capacity,
        "booked": booked,
        "available": max(0, session.capacity - booked),
        "fill_rate_pct": round(booked / session.capacity * 100, 1) if session.capacity else 0,
        "is_full": booked >= session.capacity,
        "status": session.status,
    }


@router.post("", response_model=ExamSessionRead, status_code=status.HTTP_201_CREATED)
def create_session(
    payload: ExamSessionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "super_admin")),
) -> ExamSession:
    # Le verrou du centre sérialise les créations concurrentes pour que les
    # plafonds semaine/chevauchement soient évalués sur une vue cohérente.
    center = lock_operational_center(db, payload.center_id)
    validate_session_slot(db, center, payload.starts_at, payload.capacity)
    acquire_session_reference_lock(db)
    session = ExamSession(
        reference=build_session_reference(db),
        center_id=center.id,
        starts_at=payload.starts_at,
        capacity=payload.capacity,
        status="planned",
    )
    db.add(session)
    db.flush()
    db.add(
        AuditLog(
            actor_id=current_user.id,
            action="session.created",
            entity="session",
            entity_id=session.id,
            details={
                "reference": session.reference,
                "center_id": center.id,
                "starts_at": session.starts_at.isoformat(),
                "capacity": session.capacity,
            },
        )
    )
    db.commit()
    db.refresh(session)
    return session


@router.patch("/{session_id}/open", response_model=ExamSessionRead)
def open_session(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "super_admin", "center")),
) -> ExamSession:
    session = db.scalar(select(ExamSession).where(ExamSession.id == session_id).with_for_update())
    if not session:
        raise HTTPException(status_code=404, detail="Session introuvable")
    assert_session_access(current_user, session)
    center = db.get(Center, session.center_id)
    if not center or center.status not in {"active", "accredited"}:
        raise HTTPException(status_code=409, detail="Le centre n'est plus opérationnel.")
    if session.status != "planned":
        raise HTTPException(status_code=422, detail=f"Statut actuel '{session.status}' — ouverture impossible")
    session.status = "open"
    db.add(AuditLog(actor_id=current_user.id, action="session.opened", entity="session", entity_id=session.id, details={}))
    db.commit()
    db.refresh(session)
    return session


@router.patch("/{session_id}/close", response_model=ExamSessionRead)
def close_session(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "super_admin", "center")),
) -> ExamSession:
    session = db.scalar(select(ExamSession).where(ExamSession.id == session_id).with_for_update())
    if not session:
        raise HTTPException(status_code=404, detail="Session introuvable")
    assert_session_access(current_user, session)
    if session.status not in {"planned", "open"}:
        raise HTTPException(status_code=422, detail=f"Statut actuel '{session.status}' — fermeture impossible")
    previous_status = session.status
    session.status = "closed"
    db.add(
        AuditLog(
            actor_id=current_user.id,
            action="session.closed",
            entity="session",
            entity_id=session.id,
            details={"previous_status": previous_status},
        )
    )
    db.commit()
    db.refresh(session)
    return session


@router.patch("/{session_id}/cancel", response_model=ExamSessionRead)
def cancel_session(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "super_admin")),
) -> ExamSession:
    """Annule la session et libère réellement les réservations associées.

    Un paiement déjà encaissé n'est jamais remboursé automatiquement : il est
    comptabilisé dans l'audit comme remboursement/transfert à traiter.
    """
    session = db.scalar(select(ExamSession).where(ExamSession.id == session_id).with_for_update())
    if not session:
        raise HTTPException(status_code=404, detail="Session introuvable")
    if session.status in {"closed", "archived"}:
        raise HTTPException(status_code=422, detail="Impossible d'annuler une session fermée ou archivée")
    if session.status == "cancelled":
        return session

    previous_status = session.status
    now = datetime.now(UTC).replace(tzinfo=None)
    affected = list(
        db.scalars(
            select(Booking)
            .where(Booking.session_id == session.id, Booking.status != "cancelled")
            .with_for_update()
        ).all()
    )
    paid_to_process = 0
    for booking in affected:
        if booking.status in {"paid", "checked_in"} or booking.payment_reference:
            paid_to_process += 1
        previous_booking_status = booking.status
        booking.status = "cancelled"
        booking.cancelled_at = now
        note = f"Session {session.reference} annulée; ancien statut réservation={previous_booking_status}"
        booking.notes = f"{booking.notes} | {note}" if booking.notes else note
        db.add(booking)

    session.status = "cancelled"
    db.add(session)
    db.add(
        AuditLog(
            actor_id=current_user.id,
            action="session.cancelled",
            entity="session",
            entity_id=session.id,
            details={
                "previous_status": previous_status,
                "bookings_cancelled": len(affected),
                "paid_bookings_requiring_refund_or_transfer": paid_to_process,
                "cancelled_at": now.isoformat(),
            },
        )
    )
    db.commit()
    db.refresh(session)
    return session


@router.get("/stats/by-commune", response_model=list[dict])
def get_sessions_stats_by_commune(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "super_admin")),
) -> list[dict]:
    rows = db.execute(
        select(
            Center.commune,
            Center.prefecture,
            func.count(func.distinct(Center.id)).label("centers_count"),
            func.count(ExamSession.id).label("sessions_count"),
            func.coalesce(func.sum(ExamSession.capacity), 0).label("total_capacity"),
        )
        .outerjoin(
            ExamSession,
            and_(
                ExamSession.center_id == Center.id,
                ExamSession.status.not_in(["cancelled", "archived"]),
            ),
        )
        .group_by(Center.commune, Center.prefecture)
        .order_by(Center.prefecture, Center.commune)
    ).all()

    result = []
    for row in rows:
        centers_count = int(row.centers_count or 0)
        threshold_met = centers_count >= 3
        result.append(
            {
                "commune": row.commune or "Non défini",
                "prefecture": row.prefecture or "Non défini",
                "centers_count": centers_count,
                "sessions_count": int(row.sessions_count or 0),
                "total_capacity": int(row.total_capacity or 0),
                # Nom conservé pour compatibilité UI. Il s'agit d'un indicateur
                # opérationnel, pas d'une preuve d'homologation institutionnelle.
                "compliant_3_centers": threshold_met,
                "compliance_status": "Seuil opérationnel atteint" if threshold_met else "Seuil opérationnel < 3 centres",
            }
        )
    return result


class BulkPlanRequest(BaseModel):
    center_id: str
    weeks: int = Field(default=4, ge=1, le=12)
    weekdays: list[int] = Field(min_length=1, max_length=7)
    hours: list[int] = Field(min_length=1, max_length=3)
    capacity: int = Field(default=35, ge=1, le=35)
    start_from: date | None = None

    @field_validator("weekdays")
    @classmethod
    def _valid_weekdays(cls, value: list[int]) -> list[int]:
        if any(day < 0 or day > 6 for day in value):
            raise ValueError("weekdays : valeurs 0 (lundi) à 6 (dimanche)")
        return sorted(set(value))

    @field_validator("hours")
    @classmethod
    def _valid_hours(cls, value: list[int]) -> list[int]:
        if any(hour < 7 or hour > 18 for hour in value):
            raise ValueError("hours : valeurs entre 7 et 18")
        return sorted(set(value))


@router.post("/bulk-plan", response_model=dict, status_code=status.HTTP_201_CREATED)
def bulk_plan_sessions(
    payload: BulkPlanRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "super_admin")),
) -> dict:
    center = lock_operational_center(db, payload.center_id)
    start = payload.start_from or (date.today() + timedelta(days=1))
    effective_max = min(center.max_sessions_per_week, MAX_SESSIONS_PER_WEEK)
    created: list[dict] = []
    skipped: list[dict] = []
    monday0 = start - timedelta(days=start.weekday())
    acquire_session_reference_lock(db)

    for week in range(payload.weeks):
        for weekday in payload.weekdays:
            day = monday0 + timedelta(weeks=week, days=weekday)
            if day < start:
                continue
            for hour in payload.hours:
                starts_at = datetime.combine(day, time(hour=hour))
                label = starts_at.strftime("%d/%m/%Y %Hh")
                if count_sessions_this_week(db, center.id, starts_at) >= effective_max:
                    skipped.append({"slot": label, "reason": f"max {effective_max} sessions/semaine atteint"})
                    continue
                if has_overlapping_session(db, center.id, starts_at):
                    skipped.append({"slot": label, "reason": "chevauchement avec une session existante"})
                    continue
                session = ExamSession(
                    reference=build_session_reference(db),
                    center_id=center.id,
                    starts_at=starts_at,
                    capacity=payload.capacity,
                    status="planned",
                )
                db.add(session)
                db.flush()
                created.append(
                    {
                        "session_id": session.id,
                        "reference": session.reference,
                        "starts_at": starts_at.isoformat(),
                    }
                )

    db.add(
        AuditLog(
            actor_id=current_user.id,
            action="session.bulk_planned",
            entity="session",
            entity_id=center.id,
            details={"created_count": len(created), "skipped_count": len(skipped)},
        )
    )
    db.commit()
    return {
        "center": {"id": center.id, "name": center.name},
        "created": created,
        "skipped": skipped,
        "created_count": len(created),
        "skipped_count": len(skipped),
    }


@router.get("/upcoming-by-center/{center_id}", response_model=dict)
def upcoming_sessions_by_center(
    center_id: str,
    limit: int = Query(default=30, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("center", "admin", "super_admin")),
) -> dict:
    if current_user.role == "center":
        assert_center_access(current_user, center_id)
    now = datetime.now(UTC).replace(tzinfo=None)
    sessions = list(
        db.scalars(
            select(ExamSession)
            .where(ExamSession.center_id == center_id, ExamSession.starts_at > now)
            .order_by(ExamSession.starts_at.asc())
            .limit(limit)
        ).all()
    )
    ids = [session.id for session in sessions]
    counts: dict[str, int] = {}
    if ids:
        counts = dict(
            db.execute(
                select(Booking.session_id, func.count(Booking.id))
                .where(Booking.session_id.in_(ids), Booking.status.not_in(["cancelled"]))
                .group_by(Booking.session_id)
            ).all()
        )
    items = [
        {
            "session_id": session.id,
            "reference": session.reference,
            "starts_at": session.starts_at.isoformat(),
            "capacity": session.capacity,
            "booked": counts.get(session.id, 0),
            "status": session.status,
        }
        for session in sessions
    ]
    return {"items": items, "total": len(items)}
