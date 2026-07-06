"""
WhatsApp Business Cloud API (Meta) — CodeRoute Guinée.

Envoi des notifications de résultat d'examen par WhatsApp.
Fallback console si credentials absents (dev / pilote sans compte Meta).

Variables d'env :
  WHATSAPP_PHONE_NUMBER_ID — ID du numéro (Meta Business, ex: 1055xxxxxxxxx)
  WHATSAPP_ACCESS_TOKEN    — token permanent Meta Cloud API
  WHATSAPP_API_BASE        — https://graph.facebook.com/v19.0 (défaut)

Docs : https://developers.facebook.com/docs/whatsapp/cloud-api
"""
from __future__ import annotations

import logging
import os

import httpx

log = logging.getLogger("coderoute.whatsapp")


def _normalize_gn(phone: str) -> str:
    """+224 6XX… → 2246XX… (format international sans '+' exigé par Meta)."""
    p = phone.strip().replace(" ", "").replace("-", "")
    if p.startswith("+"):
        p = p[1:]
    if p.startswith("00"):
        p = p[2:]
    if not p.startswith("224") and len(p) == 9:
        p = "224" + p
    return p


def send_whatsapp_text(phone: str, body: str) -> bool:
    """Envoie un message texte WhatsApp. Retourne True si accepté par l'API."""
    phone_id = os.environ.get("WHATSAPP_PHONE_NUMBER_ID", "")
    token = os.environ.get("WHATSAPP_ACCESS_TOKEN", "")
    api_base = os.environ.get("WHATSAPP_API_BASE", "https://graph.facebook.com/v19.0")

    to = _normalize_gn(phone)

    if not phone_id or not token:
        log.info("[WhatsApp fallback console] → %s : %s", to, body[:160])
        return False

    try:
        r = httpx.post(
            f"{api_base}/{phone_id}/messages",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json={
                "messaging_product": "whatsapp",
                "to": to,
                "type": "text",
                "text": {"preview_url": False, "body": body[:4096]},
            },
            timeout=10,
        )
        if r.status_code in (200, 201):
            return True
        log.warning("WhatsApp API %s : %s", r.status_code, r.text[:200])
        return False
    except Exception as exc:  # jamais bloquant
        log.warning("WhatsApp envoi échoué : %s", exc)
        return False


def send_exam_result_whatsapp(
    phone: str, candidate_name: str, passed: bool, score: int, total: int
) -> bool:
    verdict = "ADMIS(E) ✅" if passed else "NON ADMIS(E)"
    body = (
        f"CodeRoute Guinée — Résultat d'examen\n"
        f"{candidate_name}\n"
        f"Score : {score}/{total}\n"
        f"Résultat : {verdict}\n"
        + ("Votre certificat est disponible dans votre espace candidat."
           if passed else
           "Vous pourrez vous réinscrire pour une nouvelle session.")
    )
    return send_whatsapp_text(phone, body)
