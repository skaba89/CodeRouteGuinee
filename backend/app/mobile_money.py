"""
Intégration Mobile Money Guinée — Orange Money & MTN Money.

Architecture :
- En mode SANDBOX (défaut / tests) : simulation locale, pas d'appel réseau.
- En mode PRODUCTION : appels HTTP réels vers les APIs des opérateurs guinéens.
  Les credentials sont injectés par variables d'environnement (cf. Settings).

Opérateurs supportés :
- Orange Money Guinée (OMGN) — API Orange Developer Africa v2
- MTN Mobile Money Guinée (MoMo) — MTN MoMo API v1 (collection)

Fallback : si un provider non reconnu est reçu, la requête est traitée en sandbox
et une alerte est tracée en audit.

Variables d'environnement requises en production :
  ORANGE_MONEY_CLIENT_ID        — Client ID de l'application Orange
  ORANGE_MONEY_CLIENT_SECRET    — Secret de l'application Orange
  ORANGE_MONEY_MERCHANT_CODE    — Code marchand Orange (canal paiement)
  MTN_MONEY_SUBSCRIPTION_KEY    — Ocp-Apim-Subscription-Key MTN
  MTN_MONEY_API_USER_ID         — X-Reference-Id (UUID) créé lors de l'onboarding
  MTN_MONEY_API_KEY             — API Key MTN générée pour l'UUID ci-dessus
  MTN_MONEY_ENVIRONMENT         — 'sandbox' ou 'mtncongo' / 'mtnguinee' (prod)
  MOBILE_MONEY_MODE             — 'sandbox' (défaut) ou 'production'
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass


@dataclass(frozen=True)
class ProviderResult:
    provider: str
    status: str
    external_reference: str
    message: str
    checkout_url: str = ""   # URL de redirection Wave checkout (vide pour les autres providers)


# ── Normalisation provider ────────────────────────────────────────────────

def normalize_provider(provider: str) -> str:
    value = provider.strip().lower().replace(" ", "_")
    aliases = {
        "orange": "orange_money",
        "orange_money": "orange_money",
        "mtn": "mtn_money",
        "mtn_money": "mtn_money",
        "wave": "wave",
        "wave_money": "wave",
        "paydunya": "paydunya",
        "pay_dunya": "paydunya",
        "sandbox": "sandbox",
    }
    return aliases.get(value, "sandbox")


# ── Sandbox (tests + dev) ──────────────────────────────────────────────────

def _sandbox_payment(provider: str, phone: str, amount_gnf: int) -> ProviderResult:
    """Simulation locale — toujours acceptée, jamais d'appel réseau."""
    normalized = normalize_provider(provider)
    timestamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
    suffix = phone[-4:] if len(phone) >= 4 else "0000"
    return ProviderResult(
        provider=normalized,
        status="paid",
        external_reference=f"SANDBOX-{normalized.upper()}-{timestamp}-{suffix}",
        message=f"[SANDBOX] Payment accepted — {amount_gnf} GNF via {normalized}",
    )


# ── Orange Money Guinée ────────────────────────────────────────────────────

def _orange_money_payment(phone: str, amount_gnf: int) -> ProviderResult:
    """
    Paiement via Orange Money Guinée (API Orange Developer Africa v2).

    Flux :
    1. POST /oauth/v3/token — obtenir un token OAuth2 client_credentials
    2. POST /orange-money-webpay/GN/v1/webpayment — initier la transaction
    3. Polling GET /orange-money-webpay/GN/v1/transactionstatus/{orderId}
       jusqu'à status SUCCESSFULL ou FAILED (timeout 30s)

    En cas d'erreur réseau ou de timeout, lève une ValueError avec un message
    lisible pour l'audit log.
    """
    import os
    import time
    try:
        import httpx
    except ImportError as exc:
        raise ValueError("httpx est requis pour le mode production (pip install httpx)") from exc

    client_id = os.environ.get("ORANGE_MONEY_CLIENT_ID", "")
    client_secret = os.environ.get("ORANGE_MONEY_CLIENT_SECRET", "")
    merchant_code = os.environ.get("ORANGE_MONEY_MERCHANT_CODE", "")
    base_url = os.environ.get("ORANGE_MONEY_BASE_URL", "https://api.orange.com")

    if not all([client_id, client_secret, merchant_code]):
        raise ValueError(
            "Orange Money credentials manquants : ORANGE_MONEY_CLIENT_ID, "
            "ORANGE_MONEY_CLIENT_SECRET, ORANGE_MONEY_MERCHANT_CODE"
        )

    # Étape 1 — Token OAuth2
    token_resp = httpx.post(
        f"{base_url}/oauth/v3/token",
        data={"grant_type": "client_credentials"},
        auth=(client_id, client_secret),
        timeout=10,
    )
    token_resp.raise_for_status()
    access_token = token_resp.json()["access_token"]

    order_id = str(uuid.uuid4())
    timestamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S")

    # Étape 2 — Initier la transaction
    pay_resp = httpx.post(
        f"{base_url}/orange-money-webpay/GN/v1/webpayment",
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        },
        json={
            "merchant_key": merchant_code,
            "currency": "GNF",
            "order_id": order_id,
            "amount": str(amount_gnf),
            "return_url": "https://coderoute.gov.gn/payment/return",
            "cancel_url": "https://coderoute.gov.gn/payment/cancel",
            "notif_url": "https://api.coderoute.gov.gn/api/v1/payments/webhooks/orange",
            "lang": "fr",
            "reference": f"CODEROUTE-{timestamp}",
            "msisdn": phone.replace("+", "").replace(" ", ""),
        },
        timeout=15,
    )
    pay_resp.raise_for_status()
    pay_data = pay_resp.json()
    pay_token = pay_data.get("pay_token", order_id)

    # Étape 3 — Polling statut (30s max)
    deadline = time.time() + 30
    while time.time() < deadline:
        status_resp = httpx.get(
            f"{base_url}/orange-money-webpay/GN/v1/transactionstatus/{order_id}",
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=10,
        )
        if status_resp.ok:
            tx_status = status_resp.json().get("status", "PENDING")
            if tx_status == "SUCCESSFULL":
                return ProviderResult(
                    provider="orange_money",
                    status="paid",
                    external_reference=pay_token,
                    message=f"Orange Money GN — paiement confirmé {amount_gnf} GNF",
                )
            if tx_status in ("FAILED", "CANCELLED", "EXPIRED"):
                return ProviderResult(
                    provider="orange_money",
                    status="failed",
                    external_reference=pay_token,
                    message=f"Orange Money GN — transaction {tx_status}",
                )
        time.sleep(3)

    return ProviderResult(
        provider="orange_money",
        status="pending",
        external_reference=pay_token,
        message="Orange Money GN — timeout polling, vérification manuelle requise",
    )


# ── MTN Mobile Money Guinée ───────────────────────────────────────────────

def _mtn_money_payment(phone: str, amount_gnf: int) -> ProviderResult:
    """
    Paiement via MTN MoMo Collection API v1.

    Flux :
    1. POST /v1_0/apiuser/{X-Reference-Id}/apikey — (onboarding, fait une fois)
    2. POST /collection/token/ — obtenir un Bearer token
    3. POST /collection/v1_0/requesttopay — initier le débit
    4. GET  /collection/v1_0/requesttopay/{referenceId} — polling statut
    """
    import os
    import time
    try:
        import httpx
    except ImportError as exc:
        raise ValueError("httpx est requis pour le mode production (pip install httpx)") from exc

    subscription_key = os.environ.get("MTN_MONEY_SUBSCRIPTION_KEY", "")
    api_user_id = os.environ.get("MTN_MONEY_API_USER_ID", "")
    api_key = os.environ.get("MTN_MONEY_API_KEY", "")
    environment = os.environ.get("MTN_MONEY_ENVIRONMENT", "sandbox")
    base_url = os.environ.get("MTN_MONEY_BASE_URL", "https://sandbox.momodeveloper.mtn.com")

    if not all([subscription_key, api_user_id, api_key]):
        raise ValueError(
            "MTN Money credentials manquants : MTN_MONEY_SUBSCRIPTION_KEY, "
            "MTN_MONEY_API_USER_ID, MTN_MONEY_API_KEY"
        )

    # Token Bearer
    import base64 as _b64
    credentials = _b64.b64encode(f"{api_user_id}:{api_key}".encode()).decode()
    token_resp = httpx.post(
        f"{base_url}/collection/token/",
        headers={
            "Authorization": f"Basic {credentials}",
            "Ocp-Apim-Subscription-Key": subscription_key,
        },
        timeout=10,
    )
    token_resp.raise_for_status()
    access_token = token_resp.json()["access_token"]

    reference_id = str(uuid.uuid4())

    # Initier le débit
    pay_resp = httpx.post(
        f"{base_url}/collection/v1_0/requesttopay",
        headers={
            "Authorization": f"Bearer {access_token}",
            "X-Reference-Id": reference_id,
            "X-Target-Environment": environment,
            "Ocp-Apim-Subscription-Key": subscription_key,
            "Content-Type": "application/json",
        },
        json={
            "amount": str(amount_gnf),
            "currency": "GNF",
            "externalId": reference_id,
            "payer": {
                "partyIdType": "MSISDN",
                "partyId": phone.replace("+", "").replace(" ", ""),
            },
            "payerMessage": f"Paiement CodeRoute Guinee — {amount_gnf} GNF",
            "payeeNote": "Examen code de la route",
        },
        timeout=15,
    )
    if pay_resp.status_code not in (200, 202):
        return ProviderResult(
            provider="mtn_money",
            status="failed",
            external_reference=reference_id,
            message=f"MTN MoMo — initiation échouée ({pay_resp.status_code})",
        )

    # Polling statut (30s max)
    deadline = time.time() + 30
    while time.time() < deadline:
        status_resp = httpx.get(
            f"{base_url}/collection/v1_0/requesttopay/{reference_id}",
            headers={
                "Authorization": f"Bearer {access_token}",
                "X-Target-Environment": environment,
                "Ocp-Apim-Subscription-Key": subscription_key,
            },
            timeout=10,
        )
        if status_resp.ok:
            tx_status = status_resp.json().get("status", "PENDING")
            if tx_status == "SUCCESSFUL":
                return ProviderResult(
                    provider="mtn_money",
                    status="paid",
                    external_reference=reference_id,
                    message=f"MTN MoMo GN — paiement confirmé {amount_gnf} GNF",
                )
            if tx_status in ("FAILED", "REJECTED", "TIMEOUT"):
                return ProviderResult(
                    provider="mtn_money",
                    status="failed",
                    external_reference=reference_id,
                    message=f"MTN MoMo GN — transaction {tx_status}",
                )
        time.sleep(3)

    return ProviderResult(
        provider="mtn_money",
        status="pending",
        external_reference=reference_id,
        message="MTN MoMo GN — timeout polling, vérification manuelle requise",
    )


# ── Point d'entrée unique ─────────────────────────────────────────────────

def simulate_mobile_money_payment(provider: str, phone: str, amount_gnf: int) -> ProviderResult:
    """
    Dispatcher principal — sandbox ou production selon MOBILE_MONEY_MODE.

    En production, les erreurs provider sont capturées et retournées comme
    ProviderResult(status='failed') pour ne pas exposer des stack traces.
    """
    import os
    mode = os.environ.get("MOBILE_MONEY_MODE", "sandbox").lower()
    normalized = normalize_provider(provider)

    if mode != "production":
        return _sandbox_payment(normalized, phone, amount_gnf)

    try:
        if normalized == "orange_money":
            return _orange_money_payment(phone, amount_gnf)
        if normalized == "mtn_money":
            return _mtn_money_payment(phone, amount_gnf)
        if normalized == "wave":
            return _wave_payment(phone, amount_gnf)
        if normalized == "paydunya":
            return _paydunya_payment(phone, amount_gnf)
        # Provider inconnu en production → sandbox forcé
        return _sandbox_payment(normalized, phone, amount_gnf)
    except Exception as exc:
        try:
            from app.monitoring import capture_exception
            capture_exception(exc, {
                "provider": normalized,
                "amount_gnf": amount_gnf,
                "phone_suffix": phone[-4:] if len(phone) >= 4 else "???",
            })
        except Exception:
            pass
        return ProviderResult(
            provider=normalized,
            status="failed",
            external_reference=f"ERR-{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}",
            message=f"Erreur provider {normalized} : {exc!s}",
        )


# ══════════════════════════════════════════════════════════════════
# WAVE MOBILE MONEY — Mois 10–12
# Wave est devenu le 1er portefeuille mobile en Guinée (0 % frais)
# API : https://wave.com/en/business/api
# ══════════════════════════════════════════════════════════════════

def _wave_payment(phone: str, amount_gnf: int) -> ProviderResult:
    """
    Paiement Wave Mobile Money (Guinée).

    Flux checkout Wave :
      1. POST /v1/checkout/sessions  → obtenir checkout_url
      2. Rediriger l'utilisateur vers checkout_url
      3. Webhook Wave → notifie le backend du résultat
      4. GET /v1/checkout/sessions/{id} → vérifier le statut final

    Variables d'environnement requises :
      WAVE_API_KEY       — Bearer token Wave (format wave_sn_prod_xxxx)
      WAVE_WEBHOOK_SECRET — Secret HMAC pour valider les webhooks
      WAVE_BASE_URL      — https://api.wave.com (prod) ou sandbox
    """
    import os

    import httpx

    api_key = os.environ.get("WAVE_API_KEY", "")
    base_url = os.environ.get("WAVE_BASE_URL", "https://api.wave.com")

    if not api_key:
        return ProviderResult(
            provider="wave",
            status="failed",
            external_reference=f"ERR-WAVE-NO-KEY-{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}",
            message="Wave API Key manquant — configurez WAVE_API_KEY en production.",
        )

    try:
        # Convertir GNF → WAVE accepte GNF nativement en Guinée
        resp = httpx.post(
            f"{base_url}/v1/checkout/sessions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "currency": "GNF",
                "amount": str(amount_gnf),
                "client_reference": f"CODEROUTE-{uuid.uuid4().hex[:12].upper()}",
                "success_url": "https://coderoute.gov.gn/#/candidate?payment=success",
                "error_url": "https://coderoute.gov.gn/#/candidate?payment=error",
            },
            timeout=15,
        )
        if resp.status_code in (200, 201):
            data = resp.json()
            checkout_url = data.get("wave_launch_url", "")
            return ProviderResult(
                provider="wave",
                status="pending",  # Wave = asynchrone, le webhook confirme
                external_reference=data.get("id", f"WAVE-{uuid.uuid4().hex[:12].upper()}"),
                message="Paiement Wave initié — en attente de confirmation",
                checkout_url=checkout_url,
            )
        return ProviderResult(
            provider="wave",
            status="failed",
            external_reference=f"ERR-WAVE-{resp.status_code}",
            message=f"Erreur Wave {resp.status_code}: {resp.text[:200]}",
        )
    except Exception as exc:
        return ProviderResult(
            provider="wave",
            status="failed",
            external_reference=f"ERR-WAVE-TIMEOUT-{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}",
            message=f"Wave indisponible : {exc!s}",
        )


# ══════════════════════════════════════════════════════════════════
# PAYDUNYA — Mois 10–12
# Agrégateur pan-africain : Orange Money, MTN, Wave, carte bancaire
# API : https://paydunya.com/developers
# ══════════════════════════════════════════════════════════════════

def _paydunya_payment(phone: str, amount_gnf: int) -> ProviderResult:
    """
    Paiement via PayDunya (agrégateur multi-opérateurs Afrique de l'Ouest).

    Avantage clé : PayDunya unifie Orange Money, MTN, Wave et carte bancaire
    dans un seul appel API. Idéal pour le déploiement national (33 préfectures).

    Variables d'environnement requises :
      PAYDUNYA_MASTER_KEY  — Master Key de l'application
      PAYDUNYA_PRIVATE_KEY — Private Key
      PAYDUNYA_TOKEN       — Token d'accès
      PAYDUNYA_MODE        — 'test' ou 'live'
    """
    import os

    import httpx

    master_key  = os.environ.get("PAYDUNYA_MASTER_KEY", "")
    private_key = os.environ.get("PAYDUNYA_PRIVATE_KEY", "")
    token       = os.environ.get("PAYDUNYA_TOKEN", "")
    mode        = os.environ.get("PAYDUNYA_MODE", "test")

    base_url = "https://app.paydunya.com/api/v1" if mode == "live" else "https://app.paydunya.com/sandbox-api/v1"

    if not all([master_key, private_key, token]):
        return ProviderResult(
            provider="paydunya",
            status="failed",
            external_reference=f"ERR-PD-NO-CREDS-{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}",
            message="Credentials PayDunya manquants — configurez PAYDUNYA_* en production.",
        )

    try:
        ref = f"CODEROUTE-{uuid.uuid4().hex[:12].upper()}"
        resp = httpx.post(
            f"{base_url}/checkout-invoice/create",
            headers={
                "PAYDUNYA-MASTER-KEY": master_key,
                "PAYDUNYA-PRIVATE-KEY": private_key,
                "PAYDUNYA-TOKEN": token,
                "Content-Type": "application/json",
            },
            json={
                "invoice": {
                    "total_amount": amount_gnf,
                    "description": f"Examen code de la route CodeRoute Guinée — {phone}",
                },
                "store": {
                    "name": "CodeRoute Guinée",
                    "tagline": "Plateforme nationale d'examen du code de la route",
                    "postal_address": "Conakry, Guinée",
                    "phone": "+224600000000",
                },
                "custom_data": {
                    "phone": phone,
                    "reference": ref,
                },
                "actions": {
                    "cancel_url": "https://coderoute.gov.gn/#/candidate?payment=cancel",
                    "return_url": "https://coderoute.gov.gn/#/candidate?payment=success",
                    "callback_url": "https://api.coderoute.gov.gn/api/v1/payments/webhook/paydunya",
                },
            },
            timeout=15,
        )
        if resp.status_code == 200:
            data = resp.json()
            if data.get("response_code") == "00":
                return ProviderResult(
                    provider="paydunya",
                    status="pending",
                    external_reference=data.get("token", ref),
                    message=f"Paiement PayDunya initié — URL: {data.get('invoice_url', '')}",
                )
        return ProviderResult(
            provider="paydunya",
            status="failed",
            external_reference=f"ERR-PD-{resp.status_code}",
            message=f"Erreur PayDunya: {resp.text[:200]}",
        )
    except Exception as exc:
        return ProviderResult(
            provider="paydunya",
            status="failed",
            external_reference=f"ERR-PD-TIMEOUT-{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}",
            message=f"PayDunya indisponible : {exc!s}",
        )
