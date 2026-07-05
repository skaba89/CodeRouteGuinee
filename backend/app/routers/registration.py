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
from app.models_candidate import Candidate
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
    base = select(Candidate).where(Candidate.registered_by == current_user.id)
    total = db.scalar(select(func.count()).select_from(base.subquery())) or 0
    rows = db.scalars(
        base.order_by(Candidate.created_at.desc()).offset(offset).limit(limit)
    ).all()
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
