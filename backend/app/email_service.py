"""
Service email CodeRoute Guinée — via Brevo (API transactionnelle).

Configuration requise dans .env :
  BREVO_API_KEY=xkeysib-xxxxxxxxxxxx
  EMAIL_FROM=noreply@coderoute.gov.gn
  EMAIL_FROM_NAME=CodeRoute Guinée

Si BREVO_API_KEY est absent, les emails sont loggués en mode dev (pas d'envoi réel).

Emails envoyés :
  1. Confirmation de réservation (booking.confirmed)
  2. Convocation à l'examen J-3 (booking.convocation)
  3. Résultat d'examen (exam.result)
  4. Certificat disponible (exam.certificate)
"""
from __future__ import annotations

import logging
import os
from typing import Any

import httpx

log = logging.getLogger("coderoute.email")

_BREVO_API_URL = "https://api.brevo.com/v3/smtp/email"
_FROM_EMAIL = os.environ.get("EMAIL_FROM", "noreply@coderoute.gov.gn")
_FROM_NAME  = os.environ.get("EMAIL_FROM_NAME", "CodeRoute Guinée")


def _send(to_email: str, to_name: str, subject: str, html: str) -> bool:
    """
    Envoie un email via l'API Brevo.
    Retourne True si l'envoi est réussi, False sinon (ne lève pas d'exception).
    """
    api_key = os.environ.get("BREVO_API_KEY", "")

    if not api_key:
        # Mode développement : log sans envoi
        log.info(
            "Email (dev, non envoyé) → %s <%s> : %s",
            to_name, to_email, subject,
        )
        return True

    payload: dict[str, Any] = {
        "sender":  {"name": _FROM_NAME, "email": _FROM_EMAIL},
        "to":      [{"email": to_email, "name": to_name}],
        "subject": subject,
        "htmlContent": html,
    }

    try:
        r = httpx.post(
            _BREVO_API_URL,
            headers={
                "api-key": api_key,
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=10,
        )
        if r.status_code in (200, 201):
            log.info("Email envoyé → %s (%s)", to_email, subject)
            return True
        log.warning("Email Brevo %s → %s : HTTP %d — %s",
                    subject, to_email, r.status_code, r.text[:200])
        return False
    except Exception as exc:  # réseau, timeout, etc.
        log.error("Email Brevo échec → %s : %s", to_email, exc)
        return False


# ── Templates HTML ────────────────────────────────────────────────────────────

_BASE_STYLE = """
<style>
  body{font-family:Arial,sans-serif;background:#f4f4f4;margin:0;padding:0}
  .wrapper{max-width:600px;margin:0 auto;background:#fff;border-radius:8px;overflow:hidden}
  .header{background:#006B3F;color:#fff;padding:24px 32px}
  .header h1{margin:0;font-size:22px}
  .header p{margin:4px 0 0;opacity:.85;font-size:14px}
  .body{padding:32px}
  .body p{color:#333;line-height:1.6;margin:0 0 16px}
  .info-box{background:#f9f9f9;border-left:4px solid #006B3F;padding:16px 20px;border-radius:4px;margin:20px 0}
  .info-box strong{color:#006B3F}
  .badge{display:inline-block;padding:8px 20px;border-radius:20px;font-weight:700;font-size:18px}
  .badge.pass{background:#d4edda;color:#155724}
  .badge.fail{background:#f8d7da;color:#721c24}
  .footer{background:#f4f4f4;text-align:center;padding:16px;font-size:12px;color:#888}
  .btn{display:inline-block;background:#006B3F;color:#fff;padding:12px 28px;border-radius:6px;text-decoration:none;font-weight:700;margin-top:8px}
</style>
"""


def send_booking_confirmation(
    to_email: str,
    candidate_name: str,
    booking_reference: str,
    session_date: str,
    center_name: str,
    verification_code: str,
) -> bool:
    """Email de confirmation de réservation d'examen."""
    subject = f"✅ Réservation confirmée — {booking_reference}"
    html = f"""<!DOCTYPE html><html><head>{_BASE_STYLE}</head><body>
<div class="wrapper">
  <div class="header">
    <h1>CodeRoute Guinée</h1>
    <p>Plateforme nationale d'examen du code de la route</p>
  </div>
  <div class="body">
    <p>Bonjour <strong>{candidate_name}</strong>,</p>
    <p>Votre réservation pour l'examen du code de la route a bien été enregistrée.</p>
    <div class="info-box">
      <p><strong>Référence :</strong> {booking_reference}</p>
      <p><strong>Date de l'examen :</strong> {session_date}</p>
      <p><strong>Centre :</strong> {center_name}</p>
      <p><strong>Code de vérification :</strong> <code style="background:#e8e8e8;padding:2px 6px;border-radius:3px">{verification_code}</code></p>
    </div>
    <p>Présentez-vous au centre 30 minutes avant l'heure avec votre pièce d'identité nationale (NINA).</p>
    <p>Bonne chance !</p>
  </div>
  <div class="footer">CodeRoute Guinée — Ministère des Transports | Direction Nationale des Transports Terrestres</div>
</div>
</body></html>"""
    return _send(to_email, candidate_name, subject, html)


def send_exam_result(
    to_email: str,
    candidate_name: str,
    booking_reference: str,
    passed: bool,
    score: int,
    total: int,
    certificate_url: str | None = None,
) -> bool:
    """Email de résultat d'examen."""
    status_label = "ADMIS(E)" if passed else "AJOURNÉ(E)"
    subject = f"📋 Résultat examen CodeRoute — {status_label}"
    badge_class = "pass" if passed else "fail"
    cert_block = ""
    if passed and certificate_url:
        cert_block = f"""
    <p>Votre certificat de réussite est disponible :</p>
    <a href="{certificate_url}" class="btn">📄 Télécharger mon certificat</a>"""

    html = f"""<!DOCTYPE html><html><head>{_BASE_STYLE}</head><body>
<div class="wrapper">
  <div class="header">
    <h1>CodeRoute Guinée</h1>
    <p>Résultat de votre examen</p>
  </div>
  <div class="body">
    <p>Bonjour <strong>{candidate_name}</strong>,</p>
    <p>Voici le résultat de votre examen du code de la route (réf. {booking_reference}) :</p>
    <div style="text-align:center;margin:24px 0">
      <span class="badge {badge_class}">{status_label}</span>
      <p style="margin-top:12px;font-size:16px;color:#555">Score : <strong>{score}/{total}</strong></p>
    </div>
    {cert_block}
    {"<p>Vous pouvez vous réinscrire dès maintenant pour une nouvelle session.</p>" if not passed else ""}
  </div>
  <div class="footer">CodeRoute Guinée — Ministère des Transports</div>
</div>
</body></html>"""
    return _send(to_email, candidate_name, subject, html)


def send_payment_confirmation(
    to_email: str,
    candidate_name: str,
    booking_reference: str,
    amount_gnf: int,
    provider: str,
    receipt_number: str,
) -> bool:
    """Email de confirmation de paiement."""
    provider_labels = {
        "orange_money": "Orange Money",
        "wave":         "Wave",
        "mtn_money":    "MTN Mobile Money",
        "moov_money":   "Moov Money",
        "sandbox":      "Paiement test",
    }
    provider_label = provider_labels.get(provider, provider)
    subject = f"💳 Paiement confirmé — {receipt_number}"
    html = f"""<!DOCTYPE html><html><head>{_BASE_STYLE}</head><body>
<div class="wrapper">
  <div class="header">
    <h1>CodeRoute Guinée</h1>
    <p>Confirmation de paiement</p>
  </div>
  <div class="body">
    <p>Bonjour <strong>{candidate_name}</strong>,</p>
    <p>Votre paiement a bien été reçu.</p>
    <div class="info-box">
      <p><strong>Référence réservation :</strong> {booking_reference}</p>
      <p><strong>Reçu :</strong> {receipt_number}</p>
      <p><strong>Montant :</strong> {amount_gnf:,} GNF</p>
      <p><strong>Mode de paiement :</strong> {provider_label}</p>
    </div>
    <p>Conservez ce reçu comme preuve de paiement.</p>
  </div>
  <div class="footer">CodeRoute Guinée — Ministère des Transports</div>
</div>
</body></html>"""
    return _send(to_email, candidate_name, subject, html)


def send_convocation(
    to_email: str,
    candidate_name: str,
    booking_reference: str,
    session_date: str,
    center_name: str,
    center_address: str,
    qr_verification_url: str,
) -> bool:
    """Email de convocation J-3 avant l'examen."""
    subject = f"📅 Convocation examen CodeRoute — {session_date}"
    html = f"""<!DOCTYPE html><html><head>{_BASE_STYLE}</head><body>
<div class="wrapper">
  <div class="header">
    <h1>CodeRoute Guinée</h1>
    <p>Votre convocation à l'examen</p>
  </div>
  <div class="body">
    <p>Bonjour <strong>{candidate_name}</strong>,</p>
    <p>Votre examen du code de la route approche. Voici votre convocation officielle.</p>
    <div class="info-box">
      <p><strong>Réservation :</strong> {booking_reference}</p>
      <p><strong>Date & heure :</strong> {session_date}</p>
      <p><strong>Centre :</strong> {center_name}</p>
      <p><strong>Adresse :</strong> {center_address}</p>
    </div>
    <p><strong>À apporter obligatoirement :</strong></p>
    <ul style="color:#333;line-height:2">
      <li>Pièce d'identité nationale (NINA)</li>
      <li>Cette convocation (imprimée ou sur téléphone)</li>
      <li>Permis d'apprendre en cours de validité</li>
    </ul>
    <p>Arrivez 30 minutes avant l'heure prévue.</p>
    <a href="{qr_verification_url}" class="btn">🔍 Vérifier ma convocation en ligne</a>
  </div>
  <div class="footer">CodeRoute Guinée — Ministère des Transports</div>
</div>
</body></html>"""
    return _send(to_email, candidate_name, subject, html)


def is_configured() -> bool:
    """True si l'envoi d'emails réel est configuré (clé Brevo présente)."""
    return bool(os.environ.get("BREVO_API_KEY", "").strip())
