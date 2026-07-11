"""
Orange SMS Guinea — CodeRoute Guinée
Intégration réelle de l'API Orange SMS Guinée.

Flux :
  1. POST /oauth/v3/token → bearer access_token (OAuth2 client-credentials)
  2. POST /smsmessaging/v1/outbound/{senderAddress}/requests → envoi SMS
  3. Cache du token (60 min par défaut)
  4. Fallback console si credentials absents (dev)

Docs : https://developer.orange.com/api/sms-gu

Variables d'env :
  ORANGE_SMS_CLIENT_ID       — OAuth2 client id (portail Orange Developer)
  ORANGE_SMS_CLIENT_SECRET   — OAuth2 client secret
  ORANGE_SMS_SENDER_ADDRESS  — ex: tel:+224628000000 (numéro provisionné)
  ORANGE_SMS_API_BASE        — https://api.orange.com (défaut)
"""
from __future__ import annotations

import base64
import logging
import os
import time
from dataclasses import dataclass

import httpx

log = logging.getLogger("coderoute.orange_sms")

_API_BASE        = os.environ.get("ORANGE_SMS_API_BASE", "https://api.orange.com")
_CLIENT_ID       = os.environ.get("ORANGE_SMS_CLIENT_ID", "")
_CLIENT_SECRET   = os.environ.get("ORANGE_SMS_CLIENT_SECRET", "")
_SENDER_ADDRESS  = os.environ.get("ORANGE_SMS_SENDER_ADDRESS", "")

# ── Cache token ───────────────────────────────────────────────────────────────

@dataclass
class _TokenCache:
    token: str = ""
    expires_at: float = 0.0


_token_cache = _TokenCache()


def _get_access_token() -> str:
    """Obtient (ou réutilise) le bearer token Orange."""
    if _token_cache.token and time.time() < _token_cache.expires_at - 60:
        return _token_cache.token

    creds = base64.b64encode(f"{_CLIENT_ID}:{_CLIENT_SECRET}".encode()).decode()
    r = httpx.post(
        f"{_API_BASE}/oauth/v3/token",
        headers={
            "Authorization": f"Basic {creds}",
            "Content-Type": "application/x-www-form-urlencoded",
        },
        data={"grant_type": "client_credentials"},
        timeout=10,
    )
    r.raise_for_status()
    data = r.json()
    _token_cache.token      = data["access_token"]
    _token_cache.expires_at = time.time() + int(data.get("expires_in", 3600))
    log.info("Token Orange SMS obtenu, expire dans %ds", data.get("expires_in", 3600))
    return _token_cache.token


# ── Envoi SMS ─────────────────────────────────────────────────────────────────

@dataclass
class OrangeSmsResult:
    success: bool
    provider: str           # 'orange' | 'console'
    message_id: str = ""
    error: str = ""
    remaining_quota: int | None = None


def send_sms(recipient_phone: str, message: str) -> OrangeSmsResult:
    """
    Envoie un SMS via l'API Orange Guinea.
    En dev (credentials absents), logue en console.

    Args:
        recipient_phone: Numéro au format +224XXXXXXXXX ou 0XXXXXXXXX
        message: Texte du SMS (max 160 caractères recommandé)

    Returns:
        OrangeSmsResult
    """
    # Normaliser le numéro → tel:+224XXXXXXXXX
    phone = _normalize_phone(recipient_phone)

    # Mode console si credentials absents
    if not _CLIENT_ID or not _CLIENT_SECRET or not _SENDER_ADDRESS:
        log.info(
            "SMS (dev, non envoyé) → %s : %s",
            phone, message[:60],
        )
        return OrangeSmsResult(success=True, provider="console")

    try:
        token    = _get_access_token()
        sender   = _SENDER_ADDRESS  # tel:+224XXXXXXXXX
        url      = f"{_API_BASE}/smsmessaging/v1/outbound/{sender}/requests"
        payload  = {
            "outboundSMSMessageRequest": {
                "address":            [f"tel:{phone}"],
                "senderAddress":      sender,
                "outboundSMSTextMessage": {"message": message},
            }
        }
        r = httpx.post(
            url,
            json=payload,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            timeout=15,
        )
        r.raise_for_status()

        # Extraire l'ID et le quota restant
        data       = r.json()
        message_id = (
            data.get("outboundSMSMessageRequest", {})
                .get("resourceReference", {})
                .get("resourceURL", "")
        )
        remaining = int(r.headers.get("X-Cdr-Remaining", -1))

        log.info("SMS envoyé → %s (id: %s, quota: %s)", phone, message_id[:20], remaining)
        return OrangeSmsResult(
            success=True,
            provider="orange",
            message_id=message_id,
            remaining_quota=remaining if remaining >= 0 else None,
        )

    except Exception as exc:
        log.error("Erreur Orange SMS → %s : %s", phone, exc)
        return OrangeSmsResult(success=False, provider="orange", error=str(exc))


# ── Templates SMS ─────────────────────────────────────────────────────────────

def send_booking_confirmation_sms(phone: str, candidate_name: str,
                                   booking_ref: str, session_date: str,
                                   center_name: str) -> OrangeSmsResult:
    """SMS de confirmation de réservation."""
    msg = (
        f"CodeRoute GN: Bonjour {candidate_name}. "
        f"Reservation {booking_ref} confirmee. "
        f"Examen: {session_date} a {center_name}. "
        f"Presentez-vous 30min avant avec votre NINA."
    )
    return send_sms(phone, msg[:160])


def send_exam_reminder_sms(phone: str, candidate_name: str,
                            hours_before: int, session_date: str,
                            center_name: str) -> OrangeSmsResult:
    """SMS de rappel avant l'examen (J-24h ou J-2h)."""
    msg = (
        f"CodeRoute GN: Rappel {candidate_name}. "
        f"Votre examen est dans {hours_before}h: "
        f"{session_date} - {center_name}. "
        f"N'oubliez pas votre NINA."
    )
    return send_sms(phone, msg[:160])


def send_exam_result_sms(phone: str, candidate_name: str,
                          passed: bool, score: int, total: int) -> OrangeSmsResult:
    """SMS de résultat d'examen."""
    status = "ADMIS(E)" if passed else "AJOURNE(E)"
    msg = (
        f"CodeRoute GN: {candidate_name}, vous etes {status} "
        f"avec {score}/{total}. "
        f"{'Votre certificat est disponible sur coderoute.gov.gn' if passed else 'Reinscription possible sur coderoute.gov.gn'}"
    )
    return send_sms(phone, msg[:160])


def send_payment_confirmation_sms(phone: str, candidate_name: str,
                                   receipt_number: str, amount_gnf: int) -> OrangeSmsResult:
    """SMS de confirmation de paiement."""
    msg = (
        f"CodeRoute GN: Paiement confirme. "
        f"Recu {receipt_number}, montant {amount_gnf:,}GNF. "
        f"Merci {candidate_name}."
    )
    return send_sms(phone, msg[:160])


# ── Utilitaires ───────────────────────────────────────────────────────────────

def _normalize_phone(phone: str) -> str:
    """Normalise le numéro de téléphone au format +224XXXXXXXXX."""
    p = phone.strip().replace(" ", "").replace("-", "")
    if p.startswith("+224"):
        return p
    if p.startswith("224"):
        return "+" + p
    if p.startswith("0") and len(p) == 10:
        return "+224" + p[1:]
    if len(p) == 9:
        return "+224" + p
    return p


def is_configured() -> bool:
    """True si l'envoi de SMS réel est configuré (credentials Orange présents)."""
    return bool(
        os.environ.get("ORANGE_SMS_CLIENT_ID", "").strip()
        and os.environ.get("ORANGE_SMS_CLIENT_SECRET", "").strip()
        and os.environ.get("ORANGE_SMS_SENDER_ADDRESS", "").strip()
    )
