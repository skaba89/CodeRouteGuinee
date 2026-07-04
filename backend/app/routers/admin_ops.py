"""
Opérations d'administration pilote — réservées super_admin.

POST /api/v1/admin/ops/seed-pilote
    Déclenche le seed pilote Conakry (idempotent) sans accès Shell :
    centre Kaloum, agent centre, 50 candidats, 2 sessions, 50 réservations.

GET /api/v1/admin/ops/pilote-roster
    Liste les candidats pilote avec leur référence de réservation et leur
    code de vérification — à imprimer et distribuer le jour de l'examen.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.deps import require_roles
from app.models_booking import Booking
from app.models_candidate import Candidate
from app.models_session import ExamSession
from app.models_user import User

router = APIRouter(prefix="/admin/ops", tags=["admin-ops"])
log = logging.getLogger("coderoute.admin_ops")


@router.post("/seed-pilote")
def trigger_seed_pilote(
    current_user: User = Depends(require_roles("super_admin")),
) -> dict:
    """Lance le seed pilote Conakry. Idempotent : réexécutable sans doublon."""
    from app.seed_pilote_conakry import run
    try:
        run()
    except Exception as exc:  # remonter une erreur claire plutôt qu'un 500 brut
        log.exception("Seed pilote échoué")
        return {"status": "error", "detail": str(exc)[:300]}
    return {"status": "ok", "detail": "Seed pilote Conakry exécuté (idempotent)."}


@router.get("/pilote-roster")
def get_pilote_roster(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("center", "admin", "super_admin")),
) -> dict:
    """
    Feuille de présence pilote : candidat + référence booking + code de
    vérification + session. À imprimer pour le jour de l'examen.
    """
    rows = db.execute(
        select(Candidate, Booking, ExamSession)
        .join(Booking, Booking.candidate_id == Candidate.id)
        .join(ExamSession, ExamSession.id == Booking.session_id)
        .where(Booking.reference.like("BK-GN-CODE-B-PILOT-%"))
        .order_by(ExamSession.starts_at, Candidate.last_name)
        .limit(200)
    ).all()

    items = [
        {
            "candidate": f"{cand.first_name} {cand.last_name}",
            "phone": cand.phone,
            "identity_number": cand.identity_number,
            "booking_reference": bk.reference,
            "verification_code": bk.verification_code,
            "session": ses.reference,
            "session_starts_at": ses.starts_at.isoformat(),
            "booking_status": bk.status,
        }
        for cand, bk, ses in rows
    ]
    return {"items": items, "total": len(items)}
