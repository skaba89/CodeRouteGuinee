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
from app.models_audit import AuditLog
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


@router.post("/refresh-question-media")
def refresh_question_media(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "super_admin")),
) -> dict:
    """
    Recalcule le visuel (media_type/url/alt) de TOUTES les questions selon
    le mapping courant. À lancer après une amélioration des illustrations
    pour que les questions déjà en base bénéficient des visuels corrigés.
    """
    from app.models_question import Question
    from app.seed_full import _get_media_for_question

    updated = 0
    questions = db.scalars(select(Question)).all()
    for q in questions:
        mt, mu, ma = _get_media_for_question(q.text, q.category)
        if (q.media_type, q.media_url, q.media_alt) != (mt, mu, ma):
            q.media_type, q.media_url, q.media_alt = mt, mu, ma
            updated += 1
    db.commit()
    return {"status": "ok", "total": len(questions), "updated": updated}


@router.post("/import-wikimedia-signs")
def import_wikimedia_signs(
    validate: bool = True,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "super_admin")),
) -> dict:
    """
    Associe aux questions de signalisation les panneaux officiels français
    depuis Wikimedia Commons (domaine public).

    Pour chaque question dont le visuel SVG est un panneau connu, associe
    l'image Wikimedia correspondante (media_type=image).

    validate=True (défaut) : chaque URL est vérifiée (requête réelle) avant
    d'être appliquée. Les panneaux dont l'image ne répond pas sont IGNORÉS
    — la question garde alors son SVG. Aucune question n'est cassée.
    validate=False : applique sans vérifier (plus rapide, à réserver si le
    catalogue est déjà connu bon).
    """
    from app.models_question import Question
    from app.seed_full import _get_media_for_question
    from app.wikimedia_signs import WIKIMEDIA_SIGNS

    # 1. Valider les URLs (une seule fois par panneau, pas par question)
    valid_signs: dict[str, tuple[str, str]] = {}
    validation_report: list[dict] = []

    if validate:
        import httpx
        headers = {"User-Agent": "CodeRouteGuinee/1.0 (+https://coderoute.gov.gn)"}
        with httpx.Client(timeout=12, follow_redirects=True, headers=headers) as http:
            for sign, (url, desc) in WIKIMEDIA_SIGNS.items():
                try:
                    r = http.get(url)
                    ct = r.headers.get("content-type", "")
                    if r.status_code == 200 and ("svg" in ct or "image" in ct):
                        valid_signs[sign] = (str(r.url), desc)  # URL finale résolue
                        validation_report.append({"sign": sign, "status": "ok"})
                    else:
                        validation_report.append({"sign": sign, "status": f"skip_{r.status_code}"})
                except Exception:
                    validation_report.append({"sign": sign, "status": "skip_error"})
    else:
        valid_signs = dict(WIKIMEDIA_SIGNS)

    # 2. Associer aux questions dont le SVG correspond à un panneau validé
    #    On ne touche PAS aux questions ayant déjà un média réel (image/video
    #    posé manuellement par un admin).
    updated = 0
    skipped_has_media = 0
    questions = db.scalars(select(Question)).all()
    for q in questions:
        # Média réel déjà associé manuellement → ne pas écraser
        if q.media_type in ("image", "video") and q.media_url and "wikimedia" not in (q.media_url or ""):
            skipped_has_media += 1
            continue
        # Recalculer le panneau SVG "cible" de cette question
        mt, sign_key, _alt = _get_media_for_question(q.text, q.category)
        if mt == "sign" and sign_key in valid_signs:
            url, desc = valid_signs[sign_key]
            if q.media_url != url or q.media_type != "image":
                q.media_type = "image"
                q.media_url = url
                q.media_alt = desc
                updated += 1

    db.add(AuditLog(
        actor_id=current_user.id,
        action="question.wikimedia_import",
        entity="question",
        entity_id=None,
        details={"updated": updated, "validated_signs": len(valid_signs)},
    ))
    db.commit()

    return {
        "status": "ok",
        "validated": validate,
        "signs_available": len(valid_signs),
        "signs_total": len(WIKIMEDIA_SIGNS),
        "questions_updated": updated,
        "skipped_manual_media": skipped_has_media,
        "validation_report": validation_report,
    }


@router.get("/notifications-status")
def notifications_status(
    current_user: User = Depends(require_roles("admin", "super_admin")),
) -> dict:
    """
    État des canaux de notification : indique lesquels sont configurés
    (clés présentes) et donc actifs en envoi réel. Les canaux non
    configurés retombent en mode console (log) sans bloquer l'application.
    """
    from app.email_service import is_configured as email_ok
    from app.orange_sms import is_configured as sms_ok
    from app.whatsapp_service import is_configured as whatsapp_ok

    channels = {
        "email":    {"configured": email_ok(),    "provider": "Brevo",
                     "env_keys": ["BREVO_API_KEY"]},
        "sms":      {"configured": sms_ok(),       "provider": "Orange SMS Guinée",
                     "env_keys": ["ORANGE_SMS_CLIENT_ID", "ORANGE_SMS_CLIENT_SECRET",
                                  "ORANGE_SMS_SENDER_ADDRESS"]},
        "whatsapp": {"configured": whatsapp_ok(),  "provider": "Meta WhatsApp Cloud API",
                     "env_keys": ["WHATSAPP_PHONE_NUMBER_ID", "WHATSAPP_ACCESS_TOKEN"]},
    }
    active = [name for name, c in channels.items() if c["configured"]]
    return {
        "channels": channels,
        "active_channels": active,
        "any_active": bool(active),
    }


@router.post("/notifications-test")
def notifications_test(
    payload: dict,
    current_user: User = Depends(require_roles("super_admin")),
) -> dict:
    """
    Envoie une notification de test sur un canal donné, pour valider la
    configuration avant l'ouverture aux candidats.

    Corps : {"channel": "email"|"sms"|"whatsapp", "to": "<destinataire>"}
    """
    channel = str(payload.get("channel", "")).lower()
    to = str(payload.get("to", "")).strip()
    if channel not in ("email", "sms", "whatsapp") or not to:
        return {"ok": False, "error": "Paramètres invalides (channel, to requis)."}

    msg = "Test CodeRoute Guinée : ce canal de notification fonctionne."
    try:
        if channel == "email":
            from app.email_service import _send
            ok = _send(to, "Administrateur", "Test CodeRoute Guinée", f"<p>{msg}</p>")
        elif channel == "sms":
            from app.orange_sms import send_sms
            ok = bool(send_sms(to, msg))
        else:
            from app.whatsapp_service import send_whatsapp_text
            ok = bool(send_whatsapp_text(to, msg))
        return {"ok": ok, "channel": channel, "to": to}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "channel": channel, "error": str(exc)[:200]}
