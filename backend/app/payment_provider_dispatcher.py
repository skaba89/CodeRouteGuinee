from __future__ import annotations

import os
import uuid
from datetime import UTC, datetime

from app.mobile_money import (
    ProviderResult,
    _mtn_money_payment,
    _orange_money_payment,
    _paydunya_payment,
    _sandbox_payment,
    _wave_payment,
)

_CANONICAL_PROVIDERS = {
    "orange_money",
    "mtn_money",
    "wave",
    "paydunya",
    "celcom_money",
    "sandbox",
}
_PRODUCTION_PROVIDERS = {"orange_money", "mtn_money", "wave", "paydunya"}


def _failed(provider: str, message: str) -> ProviderResult:
    return ProviderResult(
        provider=provider or "unknown",
        status="failed",
        external_reference=f"ERR-{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:8].upper()}",
        message=message,
    )


def _celcom_money_payment_safe(phone: str, amount_gnf: int) -> ProviderResult:
    """Compat Celcom non-production avec un contrat ProviderResult toujours valide."""
    try:
        import httpx
    except ImportError as exc:
        return _failed("celcom_money", f"httpx indisponible : {exc}")

    client_id = os.environ.get("CELCOM_MONEY_CLIENT_ID", "").strip()
    client_secret = os.environ.get("CELCOM_MONEY_CLIENT_SECRET", "").strip()
    api_base = os.environ.get("CELCOM_MONEY_API_BASE", "https://api.celcom.com").rstrip("/")
    currency = os.environ.get("CELCOM_MONEY_CURRENCY", "GNF").strip() or "GNF"

    if not client_id or not client_secret:
        return _sandbox_payment("celcom_money", phone, amount_gnf)

    reference = str(uuid.uuid4())
    try:
        token_response = httpx.post(
            f"{api_base}/oauth/token",
            data={
                "grant_type": "client_credentials",
                "client_id": client_id,
                "client_secret": client_secret,
            },
            timeout=10,
        )
        token_response.raise_for_status()
        access_token = token_response.json()["access_token"]

        payment_response = httpx.post(
            f"{api_base}/payment/v1/requesttopay",
            headers={
                "Authorization": f"Bearer {access_token}",
                "X-Reference-Id": reference,
                "Content-Type": "application/json",
            },
            json={
                "amount": str(amount_gnf),
                "currency": currency,
                "externalId": reference,
                "payer": {
                    "partyIdType": "MSISDN",
                    "partyId": phone.replace("+", "").replace(" ", ""),
                },
                "payerMessage": f"CodeRoute {amount_gnf} {currency}",
                "payeeNote": "Frais code route",
            },
            timeout=30,
        )
        payment_response.raise_for_status()
        return ProviderResult(
            provider="celcom_money",
            status="pending",
            external_reference=reference,
            message=f"Celcom {amount_gnf} {currency} — en attente de confirmation",
        )
    except Exception as exc:
        return ProviderResult(
            provider="celcom_money",
            status="failed",
            external_reference=f"ERR-CELCOM-{reference}",
            message=f"Celcom indisponible : {exc!s}",
        )


def dispatch_mobile_money_payment(provider: str, phone: str, amount_gnf: int) -> ProviderResult:
    """Dispatcher applicatif fail-closed.

    Le provider doit déjà être canonique après la validation de `payment_rules`.
    Cette seconde garde empêche néanmoins tout futur appel direct de transformer
    un provider inconnu ou `sandbox` en paiement réussi en production.
    """
    normalized = (provider or "").strip().lower()
    if normalized not in _CANONICAL_PROVIDERS:
        return _failed(normalized, f"Provider non supporté : {normalized or 'vide'}")

    mode = os.environ.get("MOBILE_MONEY_MODE", "sandbox").strip().lower()
    if mode != "production":
        if normalized == "celcom_money":
            return _celcom_money_payment_safe(phone, amount_gnf)
        return _sandbox_payment(normalized, phone, amount_gnf)

    if normalized not in _PRODUCTION_PROVIDERS:
        return _failed(normalized, f"Provider {normalized} désactivé en production")

    try:
        if normalized == "orange_money":
            return _orange_money_payment(phone, amount_gnf)
        if normalized == "mtn_money":
            return _mtn_money_payment(phone, amount_gnf)
        if normalized == "wave":
            return _wave_payment(phone, amount_gnf)
        if normalized == "paydunya":
            return _paydunya_payment(phone, amount_gnf)
    except Exception as exc:
        try:
            from app.monitoring import capture_exception

            capture_exception(
                exc,
                {
                    "provider": normalized,
                    "amount_gnf": amount_gnf,
                    "phone_suffix": phone[-4:] if len(phone) >= 4 else "???",
                },
            )
        except Exception:
            pass
        return _failed(normalized, f"Erreur provider {normalized} : {exc!s}")

    return _failed(normalized, f"Provider {normalized} sans implémentation active")
