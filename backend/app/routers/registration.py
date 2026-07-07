"""
Inscription des candidats — deux parcours nationaux :

POST /api/v1/registration/candidate          (PUBLIC)
    Candidat libre : crée le compte User (role=candidate) + la fiche
    Candidate liée, et retourne les tokens (connexion immédiate) + la
    référence officielle GN-CODE-....

POST /api/v1/registration/school-candidate   (driving_school/admin/super_admin)
    Une auto-école inscrit un de ses élèves : fiche Candidate avec
    registered_by = auto-école. Compte User optionnel si email + mot de
    passe fournis.

GET  /api/v1/registration/my-candidates      (driving_school)
    Liste paginée des candidats inscrits par cette auto-école.

GET  /api/v1/registration/my-profile         (candidate)
    Fiche Candidate du candidat connecté (via user_id).
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
import re

from pydantic import BaseModel, Field, field_validator
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.routers.auth import audit_auth_event
from app.db.session import get_db
from app.deps import get_current_user, require_roles
from app.booking_service import build_booking_reference, build_verification_code
from app.models_booking import Booking
from app.models_candidate import Candidate
from app.models_center import Center
from app.models_session import ExamSession
from app.models_user import User
from app.routers.candidates import build_candidate_reference
from app.security import create_access_token, create_refresh_token, get_password_hash

router = APIRouter(prefix="/registration", tags=["registration"])
log = logging.getLogger("coderoute.registration")

PERMIT_CATEGORIES = {"A", "B", "C", "D", "E"}


# ── Schémas ──────────────────────────────────────────────────────────────────

EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")


class FreeCandidateRegisterIn(BaseModel):
    first_name: str = Field(min_length=2, max_length=120)
    last_name: str = Field(min_length=2, max_length=120)
    email: str = Field(max_length=200)
    password: str = Field(min_length=8, max_length=128)
    phone: str = Field(min_length=8, max_length=50)
    identity_number: str = Field(min_length=3, max_length=120)
    permit_category: str = "B"
    city: str | None = None
    date_of_birth: str | None = None  # ISO YYYY-MM-DD

    @field_validator("email")
    @classmethod
    def _valid_email(cls, v: str) -> str:
        v = v.strip().lower()
        if not EMAIL_RE.match(v):
            raise ValueError("Adresse email invalide")
        return v


class SchoolCandidateRegisterIn(BaseModel):
    first_name: str = Field(min_length=2, max_length=120)
    last_name: str = Field(min_length=2, max_length=120)
    phone: str = Field(min_length=8, max_length=50)
    identity_number: str = Field(min_length=3, max_length=120)
    permit_category: str = "B"
    city: str | None = None
    # Compte de connexion optionnel pour l'élève
    email: str | None = Field(default=None, max_length=200)
    password: str | None = Field(default=None, min_length=8, max_length=128)

    @field_validator("email")
    @classmethod
    def _valid_email(cls, v: str | None) -> str | None:
        if v is None or not v.strip():
            return None
        v = v.strip().lower()
        if not EMAIL_RE.match(v):
            raise ValueError("Adresse email invalide")
        return v


# ── Helpers ──────────────────────────────────────────────────────────────────

def _check_duplicates(db: Session, identity_number: str, phone: str) -> None:
    dup = db.scalar(
        select(Candidate).where(
            (Candidate.identity_number == identity_number.strip())
            | (Candidate.phone == phone.strip())
        )
    )
    if dup:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Un candidat existe déjà avec ce numéro d'identité ou ce téléphone.",
        )


def _validate_category(cat: str) -> str:
    cat = (cat or "B").strip().upper()
    if cat not in PERMIT_CATEGORIES:
        raise HTTPException(status_code=422, detail=f"Catégorie invalide : {cat}")
    return cat


def _parse_dob(raw: str | None):
    if not raw:
        return None
    from datetime import date
    try:
        return date.fromisoformat(raw)
    except ValueError:
        raise HTTPException(status_code=422, detail="date_of_birth doit être au format YYYY-MM-DD")


# ── Candidat libre (public) ──────────────────────────────────────────────────

@router.post("/candidate", status_code=status.HTTP_201_CREATED)
def register_free_candidate(
    payload: FreeCandidateRegisterIn,
    request: Request,
    db: Session = Depends(get_db),
) -> dict:
    email = payload.email.lower().strip()

    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email déjà enregistré.")
    _check_duplicates(db, payload.identity_number, payload.phone)
    category = _validate_category(payload.permit_category)

    user = User(
        email=email,
        full_name=f"{payload.first_name.strip()} {payload.last_name.strip()}",
        password_hash=get_password_hash(payload.password),
        role="candidate",
        is_active=True,
    )
    db.add(user)
    db.flush()  # user.id disponible

    candidate = Candidate(
        reference=build_candidate_reference(db),
        first_name=payload.first_name.strip(),
        last_name=payload.last_name.strip(),
        identity_number=payload.identity_number.strip(),
        phone=payload.phone.strip(),
        email=email,
        permit_category=category,
        status="registered",
        city=(payload.city or "").strip() or None,
        date_of_birth=_parse_dob(payload.date_of_birth),
        user_id=user.id,
    )
    db.add(candidate)
    audit_auth_event(db, "registration.free_candidate", email, request, user)
    db.commit()
    db.refresh(candidate)

    return {
        "access_token": create_access_token(user.id, user.role),
        "refresh_token": create_refresh_token(user.id),
        "token_type": "bearer",
        "candidate_reference": candidate.reference,
        "candidate_id": candidate.id,
    }


# ── Candidats d'auto-école ───────────────────────────────────────────────────

@router.post("/school-candidate", status_code=status.HTTP_201_CREATED)
def register_school_candidate(
    payload: SchoolCandidateRegisterIn,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("driving_school", "admin", "super_admin")),
) -> dict:
    _check_duplicates(db, payload.identity_number, payload.phone)
    category = _validate_category(payload.permit_category)

    linked_user_id: str | None = None
    if payload.email:
        email = payload.email.lower().strip()
        if db.scalar(select(User).where(User.email == email)):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email déjà enregistré.")
        if not payload.password:
            raise HTTPException(status_code=422, detail="password requis si email fourni.")
        student = User(
            email=email,
            full_name=f"{payload.first_name.strip()} {payload.last_name.strip()}",
            password_hash=get_password_hash(payload.password),
            role="candidate",
            is_active=True,
        )
        db.add(student)
        db.flush()
        linked_user_id = student.id

    candidate = Candidate(
        reference=build_candidate_reference(db),
        first_name=payload.first_name.strip(),
        last_name=payload.last_name.strip(),
        identity_number=payload.identity_number.strip(),
        phone=payload.phone.strip(),
        email=(payload.email or "").lower().strip() or None,
        permit_category=category,
        status="registered",
        city=(payload.city or "").strip() or None,
        user_id=linked_user_id,
        registered_by=current_user.id,
    )
    db.add(candidate)
    audit_auth_event(db, "registration.school_candidate", candidate.phone, request, current_user)
    db.commit()
    db.refresh(candidate)

    return {
        "candidate_id": candidate.id,
        "candidate_reference": candidate.reference,
        "has_login": linked_user_id is not None,
    }


@router.get("/my-candidates")
def list_my_school_candidates(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("driving_school")),
) -> dict:
    from app.models_exam_attempt import ExamAttempt

    base = select(Candidate).where(Candidate.registered_by == current_user.id)
    total = db.scalar(select(func.count()).select_from(base.subquery())) or 0
    rows = db.scalars(
        base.order_by(Candidate.created_at.desc()).offset(offset).limit(limit)
    ).all()

    def _last_result(cand: Candidate) -> dict | None:
        att = db.scalar(
            select(ExamAttempt)
            .where(ExamAttempt.candidate_id == cand.id,
                   ExamAttempt.status == "submitted")
            .order_by(ExamAttempt.submitted_at.desc())
            .limit(1)
        )
        if not att:
            return None
        return {
            "passed": bool(att.passed),
            "score": att.score,
            "submitted_at": att.submitted_at.isoformat() if att.submitted_at else None,
        }

    return {
        "items": [
            {
                "id": c.id,
                "reference": c.reference,
                "first_name": c.first_name,
                "last_name": c.last_name,
                "phone": c.phone,
                "permit_category": c.permit_category,
                "status": c.status,
                "has_login": c.user_id is not None,
                "last_result": _last_result(c),
            }
            for c in rows
        ],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/my-profile")
def get_my_candidate_profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    if current_user.role != "candidate":
        raise HTTPException(status_code=403, detail="Réservé aux comptes candidat.")
    cand = db.scalar(select(Candidate).where(Candidate.user_id == current_user.id))
    if not cand:
        raise HTTPException(status_code=404, detail="Aucune fiche candidat liée à ce compte.")
    return {
        "id": cand.id,
        "reference": cand.reference,
        "first_name": cand.first_name,
        "last_name": cand.last_name,
        "phone": cand.phone,
        "permit_category": cand.permit_category,
        "status": cand.status,
    }


# ── Prise de rendez-vous candidat (self-service) ─────────────────────────────

def _get_my_candidate(db: Session, current_user: User) -> Candidate:
    """Fiche Candidate du compte connecté : par user_id, sinon par email (compat)."""
    cand = db.scalar(select(Candidate).where(Candidate.user_id == current_user.id))
    if not cand and current_user.email:
        cand = db.scalar(select(Candidate).where(Candidate.email == current_user.email))
    if not cand:
        raise HTTPException(
            status_code=404,
            detail="Aucune fiche candidat liée à ce compte. Complétez votre inscription.",
        )
    return cand


def _seats_taken(db: Session, session_id: str) -> int:
    return db.scalar(
        select(func.count(Booking.id)).where(
            Booking.session_id == session_id,
            Booking.status.not_in(["cancelled"]),
        )
    ) or 0


@router.get("/availability")
def get_availability(
    prefecture: str | None = Query(default=None),
    center_id: str | None = Query(default=None),
    limit: int = Query(default=60, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    Sessions futures ouvertes avec les places restantes, groupées par centre.
    Filtrable par préfecture ou centre précis.
    """
    from datetime import datetime, UTC
    now = datetime.now(UTC).replace(tzinfo=None)

    q = (
        select(ExamSession, Center)
        .join(Center, ExamSession.center_id == Center.id)
        .where(
            ExamSession.starts_at > now,
            ExamSession.status.in_(["planned", "open"]),
        )
        .order_by(ExamSession.starts_at.asc())
        .limit(limit * 2)  # marge : certaines seront pleines
    )
    if center_id:
        q = q.where(ExamSession.center_id == center_id)
    if prefecture:
        q = q.where(Center.prefecture == prefecture)

    items = []
    for ses, ctr in db.execute(q).all():
        taken = _seats_taken(db, ses.id)
        seats_left = max(0, (ses.capacity or 0) - taken)
        if seats_left <= 0:
            continue
        items.append({
            "session_id": ses.id,
            "session_reference": ses.reference,
            "starts_at": ses.starts_at.isoformat(),
            "capacity": ses.capacity,
            "seats_left": seats_left,
            "center_id": ctr.id,
            "center_name": ctr.name,
            "center_city": ctr.city,
            "center_prefecture": ctr.prefecture,
            "center_commune": ctr.commune,
        })
        if len(items) >= limit:
            break

    # Liste des préfectures qui ont au moins une session à venir (pour le filtre UI)
    prefectures = sorted({i["center_prefecture"] for i in items if i["center_prefecture"]})
    return {"items": items, "total": len(items), "prefectures": prefectures}


class BookSessionIn(BaseModel):
    session_id: str = Field(min_length=8, max_length=64)


@router.post("/book", status_code=status.HTTP_201_CREATED)
def book_session(
    payload: BookSessionIn,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("candidate")),
) -> dict:
    """
    Le candidat connecté réserve une place dans une session.
    Règles : 1 réservation active max ; capacité vérifiée ; le candidate_id
    vient TOUJOURS de la fiche liée au compte (jamais du frontend).
    """
    from datetime import datetime, UTC
    cand = _get_my_candidate(db, current_user)

    ses = db.get(ExamSession, payload.session_id)
    if not ses or ses.status not in ("planned", "open"):
        raise HTTPException(status_code=404, detail="Session introuvable ou fermée.")
    now = datetime.now(UTC).replace(tzinfo=None)
    if ses.starts_at <= now:
        raise HTTPException(status_code=409, detail="Cette session est déjà passée.")

    # Une seule réservation active (non annulée, session future)
    active = db.execute(
        select(Booking)
        .join(ExamSession, ExamSession.id == Booking.session_id)
        .where(
            Booking.candidate_id == cand.id,
            Booking.status.not_in(["cancelled"]),
            ExamSession.starts_at > now,
        )
    ).first()
    if active:
        raise HTTPException(
            status_code=409,
            detail="Vous avez déjà une réservation active. Annulez-la avant d'en créer une autre.",
        )

    # Capacité (re-vérifiée juste avant l'insertion)
    if _seats_taken(db, ses.id) >= (ses.capacity or 0):
        raise HTTPException(status_code=409, detail="Cette session est complète.")

    sequence_number = (db.scalar(select(func.count(Booking.id))) or 0) + 1
    reference = build_booking_reference(sequence_number)
    booking = Booking(
        reference=reference,
        candidate_id=cand.id,
        session_id=ses.id,
        status="confirmed",
        verification_code=build_verification_code(reference),
        notes="Réservation en ligne (self-service candidat)",
    )
    db.add(booking)
    audit_auth_event(db, "registration.self_booking", cand.phone, request, current_user)
    db.commit()
    db.refresh(booking)

    center = db.get(Center, ses.center_id)

    # Notifications best-effort (email + SMS) — non bloquantes
    try:
        if cand.email:
            from app.email_service import send_booking_confirmation
            send_booking_confirmation(
                to_email=cand.email,
                candidate_name=f"{cand.first_name} {cand.last_name}",
                booking_reference=booking.reference,
                session_date=ses.starts_at.strftime("%d/%m/%Y à %Hh%M"),
                center_name=center.name if center else "",
                verification_code=booking.verification_code,
            )
    except Exception:
        pass

    return {
        "booking_reference": booking.reference,
        "verification_code": booking.verification_code,
        "status": booking.status,
        "session_reference": ses.reference,
        "starts_at": ses.starts_at.isoformat(),
        "center_name": center.name if center else None,
        "center_city": center.city if center else None,
    }


# ── Inscription publique auto-école (validation DNTT requise) ────────────────

class SchoolRegisterIn(BaseModel):
    school_name: str = Field(min_length=3, max_length=160)
    manager_name: str = Field(min_length=3, max_length=120)
    email: str = Field(max_length=200)
    phone: str = Field(min_length=8, max_length=50)
    city: str = Field(min_length=2, max_length=120)
    password: str = Field(min_length=8, max_length=128)

    @field_validator("email")
    @classmethod
    def _valid_email(cls, v: str) -> str:
        v = v.strip().lower()
        if not EMAIL_RE.match(v):
            raise ValueError("Adresse email invalide")
        return v


@router.post("/school", status_code=status.HTTP_201_CREATED)
def register_school(
    payload: SchoolRegisterIn,
    request: Request,
    db: Session = Depends(get_db),
) -> dict:
    """
    Inscription publique d'une auto-école.
    Le compte est créé DÉSACTIVÉ (is_active=False) : la DNTT le valide
    depuis l'administration avant que l'école puisse se connecter.
    """
    email = payload.email
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email déjà enregistré.")

    school = User(
        email=email,
        full_name=f"{payload.school_name.strip()} — {payload.manager_name.strip()}",
        password_hash=get_password_hash(payload.password),
        role="driving_school",
        is_active=False,   # ← validation DNTT requise
    )
    db.add(school)
    db.flush()

    from app.models_audit import AuditLog
    db.add(AuditLog(
        actor_id=school.id,
        action="registration.school_pending",
        entity="user",
        entity_id=school.id,
        details={
            "school_name": payload.school_name.strip(),
            "manager_name": payload.manager_name.strip(),
            "phone": payload.phone.strip(),
            "city": payload.city.strip(),
            "email": email,
        },
    ))
    audit_auth_event(db, "registration.school", email, request, school)
    db.commit()

    return {
        "status": "pending_validation",
        "detail": "Votre demande a été enregistrée. La DNTT validera votre compte "
                  "sous 48h ouvrées — vous pourrez alors vous connecter.",
    }
