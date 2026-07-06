"""
Router sessions d'examen — Règles métier DNTT CodeRoute Guinée.

Règles :
  - Capacité max par session : 35 candidats
  - Max 3 sessions par semaine et par centre
  - Sessions simultanées entre centres : autorisées
  - Chevauchement horaire dans le MÊME centre : interdit
"""
from __future__ import annotations

from datetime import UTC, date, datetime, time, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.deps import get_current_user, require_roles
from app.models_center import Center
from app.models_session import ExamSession
from app.models_user import User
from app.schemas import ExamSessionCreate, ExamSessionRead

router = APIRouter(prefix="/sessions", tags=["sessions"])

MAX_CAPACITY = 35          # Règle DNTT : maximum 35 candidats par session
MAX_SESSIONS_PER_WEEK = 3  # Règle DNTT : maximum 3 sessions par semaine et par centre
SESSION_DURATION_HOURS = 2 # Durée d'une session (préparation + 30min examen + sortie)


def build_session_reference(db: Session) -> str:
    count = (db.scalar(select(func.count(ExamSession.id))) or 0) + 1
    return f"GN-SESSION-{datetime.now(UTC).year}-{count:06d}"


def _count_sessions_this_week(db: Session, center_id: str, starts_at: datetime) -> int:
    """Compte le nombre de sessions dans la même semaine ISO que starts_at pour ce centre."""
    # Semaine ISO : lundi au dimanche
    # SQLite : strftime('%W') retourne la semaine calendaire (0-53)
    # PostgreSQL : EXTRACT(WEEK FROM ...) utilise la semaine ISO
    # On utilise une fenêtre de 7 jours pour la compatibilité
    week_start = starts_at - timedelta(days=starts_at.weekday())  # Lundi
    week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)
    week_end = week_start + timedelta(days=7)

    return db.scalar(
        select(func.count(ExamSession.id)).where(
            and_(
                ExamSession.center_id == center_id,
                ExamSession.starts_at >= week_start,
                ExamSession.starts_at < week_end,
                ExamSession.status.not_in(["cancelled", "archived"]),
            )
        )
    ) or 0


def _has_overlapping_session(db: Session, center_id: str, starts_at: datetime, exclude_id: str | None = None) -> bool:
    """Vérifie qu'aucune session ne chevauche dans le même centre (2h de buffer)."""
    window_start = starts_at - timedelta(hours=SESSION_DURATION_HOURS)
    window_end = starts_at + timedelta(hours=SESSION_DURATION_HOURS)

    q = select(ExamSession.id).where(
        and_(
            ExamSession.center_id == center_id,
            ExamSession.starts_at > window_start,
            ExamSession.starts_at < window_end,
            ExamSession.status.not_in(["cancelled", "archived"]),
        )
    )
    if exclude_id:
        q = q.where(ExamSession.id != exclude_id)
    return db.scalar(q) is not None


@router.get("", response_model=dict)
def list_sessions(
    center_id: str | None = Query(default=None),
    commune: str | None = Query(default=None, description="Filtrer par commune"),
    prefecture: str | None = Query(default=None, description="Filtrer par préfecture"),
    week_offset: int | None = Query(default=None, description="0 = cette semaine, 1 = semaine prochaine"),
    session_status: str | None = Query(default=None, alias="status"),
    search: str | None = Query(default=None, description="Recherche sur l'ID ou centre"),
    limit: int = Query(default=20, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    Liste les sessions avec filtres optionnels.
    Supporte le filtrage par commune, préfecture et semaine.
    """
    q = select(ExamSession).order_by(ExamSession.starts_at.asc())

    # Si l'utilisateur est un agent de centre → restreindre à son centre uniquement
    if current_user.role == "center" and hasattr(current_user, "center_id") and current_user.center_id:
        q = q.where(ExamSession.center_id == current_user.center_id)
    elif center_id:
        q = q.where(ExamSession.center_id == center_id)

    if commune or prefecture:
        q = q.join(Center, ExamSession.center_id == Center.id)
        if commune:
            q = q.where(Center.commune == commune)
        if prefecture:
            q = q.where(Center.prefecture == prefecture)

    if week_offset is not None:
        now = datetime.now(UTC).replace(tzinfo=None)
        week_start = now - timedelta(days=now.weekday()) + timedelta(weeks=week_offset)
        week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)
        week_end = week_start + timedelta(days=7)
        q = q.where(
            and_(ExamSession.starts_at >= week_start, ExamSession.starts_at < week_end)
        )

    if session_status:
        q = q.where(ExamSession.status == session_status)
    if search:
        q = q.where(ExamSession.id.ilike(f"%{search}%"))
    total = db.scalar(select(func.count()).select_from(q.subquery()))
    raw_items = list(db.scalars(q.offset(offset).limit(limit)).all())
    items = [ExamSessionRead.model_validate(x) for x in raw_items]
    return {"items": items, "total": total, "limit": limit, "offset": offset, "search": search}


@router.get("/available", response_model=list[ExamSessionRead])
def list_available_sessions(
    commune: str | None = Query(default=None),
    prefecture: str | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[ExamSession]:
    """Sessions futures avec places disponibles — pour la réservation candidat."""
    from app.models_booking import Booking

    now = datetime.now(UTC).replace(tzinfo=None)
    q = (
        select(ExamSession)
        .where(
            and_(
                ExamSession.starts_at > now,
                ExamSession.status.in_(["planned", "open"]),
            )
        )
        .order_by(ExamSession.starts_at.asc())
    )

    if commune or prefecture:
        q = q.join(Center, ExamSession.center_id == Center.id)
        if commune:
            q = q.where(Center.commune == commune)
        if prefecture:
            q = q.where(Center.prefecture == prefecture)

    sessions = list(db.scalars(q).all())

    # Filtrer celles qui ont encore de la capacité
    result = []
    for s in sessions:
        booked = db.scalar(
            select(func.count(Booking.id)).where(
                and_(
                    Booking.session_id == s.id,
                    Booking.status.not_in(["cancelled"]),
                )
            )
        ) or 0
        if booked < s.capacity:
            result.append(s)

    return result


@router.get("/week-schedule", response_model=dict)
def get_week_schedule(
    week_offset: int = Query(default=0),
    prefecture: str | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    Vue calendrier de la semaine : toutes les sessions par jour, par centre.
    Permet de voir les sessions simultanées dans différents centres.
    """
    now = datetime.now(UTC).replace(tzinfo=None)
    week_start = now - timedelta(days=now.weekday()) + timedelta(weeks=week_offset)
    week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)
    week_end = week_start + timedelta(days=7)

    q = (
        select(ExamSession, Center)
        .join(Center, ExamSession.center_id == Center.id)
        .where(
            and_(
                ExamSession.starts_at >= week_start,
                ExamSession.starts_at < week_end,
                ExamSession.status.not_in(["cancelled", "archived"]),
            )
        )
        .order_by(ExamSession.starts_at.asc())
    )
    if prefecture:
        q = q.where(Center.prefecture == prefecture)

    rows = db.execute(q).all()

    # Grouper par jour (lundi=0 à dimanche=6)
    days = {i: [] for i in range(7)}
    for session, center in rows:
        day_idx = session.starts_at.weekday()
        days[day_idx].append({
            "session_id": session.id,
            "reference": session.reference,
            "center_id": center.id,
            "center_name": center.name,
            "commune": center.commune,
            "prefecture": center.prefecture,
            "starts_at": session.starts_at.isoformat(),
            "capacity": session.capacity,
            "status": session.status,
        })

    day_names = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]
    return {
        "week_start": week_start.isoformat(),
        "week_end": week_end.isoformat(),
        "total_sessions": sum(len(v) for v in days.values()),
        "simultaneous_peak": max((len(v) for v in days.values()), default=0),
        "days": {
            day_names[i]: {
                "date": (week_start + timedelta(days=i)).date().isoformat(),
                "sessions": sessions,
                "centers_count": len({s["center_id"] for s in sessions}),
            }
            for i, sessions in days.items()
        },
    }


@router.get("/{session_id}", response_model=ExamSessionRead)
def get_session(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "super_admin", "center")),
) -> ExamSession:
    """Récupère une session d'examen par son ID."""
    session = db.get(ExamSession, session_id)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session introuvable")
    return session


@router.get("/{session_id}/capacity-status", response_model=dict)
def get_session_capacity(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Statut de remplissage en temps réel d'une session."""
    from app.models_booking import Booking

    session = db.scalar(select(ExamSession).where(ExamSession.id == session_id))
    if not session:
        raise HTTPException(status_code=404, detail="Session introuvable")

    booked = db.scalar(
        select(func.count(Booking.id)).where(
            and_(
                Booking.session_id == session_id,
                Booking.status.not_in(["cancelled"]),
            )
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
    """
    Crée une session d'examen avec validation des règles DNTT :
      1. Capacité max 35 candidats
      2. Max 3 sessions par semaine pour ce centre
      3. Pas de chevauchement horaire dans le même centre (fenêtre 2h)
      4. Le centre doit être agréé (status=accredited)
    Note : Les sessions simultanées dans différents centres sont autorisées.
    """
    # Vérifier que le centre existe et est agréé
    center = db.scalar(select(Center).where(Center.id == payload.center_id))
    if not center:
        raise HTTPException(status_code=404, detail="Centre introuvable")
    if center.status not in ("accredited", "active"):
        raise HTTPException(
            status_code=422,
            detail=f"Le centre '{center.name}' n'est pas agréé (statut: {center.status}). "
                   "Seuls les centres agréés peuvent organiser des examens.",
        )

    # Règle 1 : capacité max 35
    if payload.capacity > MAX_CAPACITY:
        raise HTTPException(
            status_code=422,
            detail=f"La capacité maximale par session est de {MAX_CAPACITY} candidats (DNTT). "
                   f"Valeur reçue : {payload.capacity}.",
        )

    # Règle 2 : max 3 sessions par semaine par centre
    effective_max = min(center.max_sessions_per_week, MAX_SESSIONS_PER_WEEK)
    sessions_this_week = _count_sessions_this_week(db, payload.center_id, payload.starts_at)
    if sessions_this_week >= effective_max:
        raise HTTPException(
            status_code=422,
            detail=f"Ce centre a déjà {sessions_this_week} session(s) planifiée(s) cette semaine. "
                   f"Maximum autorisé : {effective_max} sessions/semaine (DNTT). "
                   "Choisissez une autre semaine ou un autre centre.",
        )

    # Règle 3 : pas de chevauchement dans le même centre
    if _has_overlapping_session(db, payload.center_id, payload.starts_at):
        raise HTTPException(
            status_code=422,
            detail=f"Une session est déjà planifiée dans ce centre dans un créneau trop proche "
                   f"(fenêtre de {SESSION_DURATION_HOURS}h). "
                   "Choisissez un créneau différent ou un autre centre. "
                   "Les sessions simultanées sont autorisées dans des centres différents.",
        )

    session = ExamSession(
        reference=build_session_reference(db),
        center_id=payload.center_id,
        starts_at=payload.starts_at,
        capacity=payload.capacity,
        status="planned",
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


@router.patch("/{session_id}/open", response_model=ExamSessionRead)
def open_session(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "super_admin", "center")),
) -> ExamSession:
    """Ouvre une session (les réservations deviennent actives)."""
    session = db.scalar(select(ExamSession).where(ExamSession.id == session_id))
    if not session:
        raise HTTPException(status_code=404, detail="Session introuvable")
    if session.status != "planned":
        raise HTTPException(status_code=422, detail=f"Statut actuel '{session.status}' — ne peut pas ouvrir")
    session.status = "open"
    db.commit()
    db.refresh(session)
    return session


@router.patch("/{session_id}/close", response_model=ExamSessionRead)
def close_session(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "super_admin", "center")),
) -> ExamSession:
    """Ferme une session (plus de réservations)."""
    session = db.scalar(select(ExamSession).where(ExamSession.id == session_id))
    if not session:
        raise HTTPException(status_code=404, detail="Session introuvable")
    session.status = "closed"
    db.commit()
    db.refresh(session)
    return session


@router.patch("/{session_id}/cancel", response_model=ExamSessionRead)
def cancel_session(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "super_admin")),
) -> ExamSession:
    """Annule une session (libère les places, notifie les candidats)."""
    session = db.scalar(select(ExamSession).where(ExamSession.id == session_id))
    if not session:
        raise HTTPException(status_code=404, detail="Session introuvable")
    if session.status in ("closed", "archived"):
        raise HTTPException(status_code=422, detail="Impossible d'annuler une session fermée ou archivée")
    session.status = "cancelled"
    db.commit()
    db.refresh(session)
    return session


@router.get("/stats/by-commune", response_model=list[dict])
def get_sessions_stats_by_commune(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "super_admin")),
) -> list[dict]:
    """
    Statistiques des sessions par commune — pour vérifier la règle
    '3 centres minimum par commune' et l'équilibre de la charge.
    """
    rows = db.execute(
        select(
            Center.commune,
            Center.prefecture,
            func.count(Center.id).label("centers_count"),
            func.count(ExamSession.id).label("sessions_count"),
            func.sum(ExamSession.capacity).label("total_capacity"),
        )
        .outerjoin(ExamSession, and_(
            ExamSession.center_id == Center.id,
            ExamSession.status.not_in(["cancelled", "archived"]),
        ))
        .group_by(Center.commune, Center.prefecture)
        .order_by(Center.prefecture, Center.commune)
    ).all()

    result = []
    for row in rows:
        compliant = (row.centers_count or 0) >= 3
        result.append({
            "commune": row.commune or "Non défini",
            "prefecture": row.prefecture or "Non défini",
            "centers_count": row.centers_count or 0,
            "sessions_count": row.sessions_count or 0,
            "total_capacity": row.total_capacity or 0,
            "compliant_3_centers": compliant,
            "compliance_status": "✅ Conforme" if compliant else "❌ < 3 centres requis",
        })
    return result


# ══════════════════════════════════════════════════════════════════════════════
# Planification en masse — programmer plusieurs semaines de sessions d'un coup
# ══════════════════════════════════════════════════════════════════════════════

class BulkPlanRequest(BaseModel):
    center_id: str
    weeks: int = Field(default=4, ge=1, le=12)          # nombre de semaines à planifier
    weekdays: list[int] = Field(min_length=1, max_length=6)  # 0=lundi … 5=samedi
    hours: list[int] = Field(min_length=1, max_length=3)     # ex: [9, 14]
    capacity: int = Field(default=35, ge=1, le=35)
    start_from: date | None = None                       # défaut : demain

    @field_validator("weekdays")
    @classmethod
    def _valid_weekdays(cls, v: list[int]) -> list[int]:
        if any(d < 0 or d > 6 for d in v):
            raise ValueError("weekdays : valeurs 0 (lundi) à 6 (dimanche)")
        return sorted(set(v))

    @field_validator("hours")
    @classmethod
    def _valid_hours(cls, v: list[int]) -> list[int]:
        if any(h < 7 or h > 18 for h in v):
            raise ValueError("hours : valeurs entre 7 et 18")
        return sorted(set(v))


@router.post("/bulk-plan", response_model=dict, status_code=status.HTTP_201_CREATED)
def bulk_plan_sessions(
    payload: BulkPlanRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "super_admin")),
) -> dict:
    """
    Planifie des sessions récurrentes sur plusieurs semaines en appliquant
    les MÊMES règles DNTT que la création unitaire :
      max 35 candidats, max 3 sessions/semaine/centre, pas de chevauchement 2h.
    Les créneaux refusés sont rapportés avec leur raison (pas d'échec global).
    """
    center = db.scalar(select(Center).where(Center.id == payload.center_id))
    if not center:
        raise HTTPException(status_code=404, detail="Centre introuvable")
    if center.status not in ("accredited", "active"):
        raise HTTPException(
            status_code=422,
            detail=f"Le centre '{center.name}' n'est pas agréé (statut: {center.status}).",
        )

    from datetime import timedelta as _td
    start = payload.start_from or (date.today() + _td(days=1))
    effective_max = min(center.max_sessions_per_week, MAX_SESSIONS_PER_WEEK)

    created: list[dict] = []
    skipped: list[dict] = []

    # Aligner sur le lundi de la semaine de départ
    monday0 = start - _td(days=start.weekday())

    for week in range(payload.weeks):
        for wd in payload.weekdays:
            day = monday0 + _td(weeks=week, days=wd)
            if day < start:
                continue  # jours déjà passés dans la première semaine
            for hour in payload.hours:
                starts_at = datetime.combine(day, time(hour=hour))
                label = starts_at.strftime("%d/%m/%Y %Hh")

                if _count_sessions_this_week(db, center.id, starts_at) >= effective_max:
                    skipped.append({"slot": label, "reason": f"max {effective_max} sessions/semaine atteint"})
                    continue
                if _has_overlapping_session(db, center.id, starts_at):
                    skipped.append({"slot": label, "reason": "chevauchement avec une session existante"})
                    continue

                s = ExamSession(
                    reference=build_session_reference(db),
                    center_id=center.id,
                    starts_at=starts_at,
                    capacity=payload.capacity,
                    status="planned",
                )
                db.add(s)
                db.flush()  # visible pour les contrôles des itérations suivantes
                created.append({"session_id": s.id, "reference": s.reference, "starts_at": starts_at.isoformat()})

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
    """Sessions à venir d'un centre avec le nombre de réservations — vue admin."""
    from app.models_booking import Booking as _Bk

    now = datetime.now(UTC).replace(tzinfo=None)
    sessions = db.scalars(
        select(ExamSession)
        .where(ExamSession.center_id == center_id, ExamSession.starts_at > now)
        .order_by(ExamSession.starts_at.asc())
        .limit(limit)
    ).all()

    items = []
    for s in sessions:
        booked = db.scalar(
            select(func.count(_Bk.id)).where(
                _Bk.session_id == s.id, _Bk.status.not_in(["cancelled"])
            )
        ) or 0
        items.append({
            "session_id": s.id, "reference": s.reference,
            "starts_at": s.starts_at.isoformat(), "capacity": s.capacity,
            "booked": booked, "status": s.status,
        })
    return {"items": items, "total": len(items)}
