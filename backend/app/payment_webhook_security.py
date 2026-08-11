from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import time
from urllib.parse import parse_qs

from fastapi import HTTPException, status

from app.core.config import get_settings


def verify_wave_signature(body: bytes, signature_header: str, *, tolerance_seconds: int = 300) -> None:
    """Valide le format Wave `t=<unix>,v1=<hmac>` et bloque les replays."""
    secret = os.environ.get("WAVE_WEBHOOK_SECRET", "").strip()
    settings = get_settings()
    if not secret:
        if settings.is_production:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="WAVE_WEBHOOK_SECRET non configuré : webhook désactivé en production",
            )
        return

    timestamp_value: str | None = None
    signatures: list[str] = []
    for part in (signature_header or "").split(","):
        key, sep, value = part.strip().partition("=")
        if not sep:
            continue
        if key == "t":
            timestamp_value = value
        elif key == "v1" and value:
            signatures.append(value)

    try:
        timestamp = int(timestamp_value or "")
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Signature Wave invalide") from exc

    if not signatures or abs(int(time.time()) - timestamp) > tolerance_seconds:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Signature Wave expirée ou invalide")

    signed_payload = str(timestamp).encode("utf-8") + body
    expected = hmac.new(secret.encode("utf-8"), signed_payload, hashlib.sha256).hexdigest()
    if not any(hmac.compare_digest(expected, candidate) for candidate in signatures):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Signature Wave invalide")


def _assign_nested(target: dict, encoded_key: str, value: str) -> None:
    parts = re.findall(r"[^\[\]]+", encoded_key)
    if not parts:
        return
    node = target
    for part in parts[:-1]:
        child = node.get(part)
        if not isinstance(child, dict):
            child = {}
            node[part] = child
        node = child
    node[parts[-1]] = value


def parse_paydunya_payload(body: bytes, content_type: str = "") -> dict:
    """Accepte le callback officiel form-urlencoded et le JSON legacy des tests."""
    if "application/json" in (content_type or "").lower():
        try:
            parsed = json.loads(body)
            return parsed if isinstance(parsed, dict) else {}
        except (json.JSONDecodeError, UnicodeDecodeError):
            return {}

    try:
        form = parse_qs(body.decode("utf-8"), keep_blank_values=True)
    except UnicodeDecodeError:
        return {}

    result: dict = {}
    for key, values in form.items():
        value = values[-1] if values else ""
        if key == "data" and value:
            try:
                nested = json.loads(value)
            except json.JSONDecodeError:
                nested = None
            if isinstance(nested, dict):
                result["data"] = nested
                continue
        _assign_nested(result, key, value)
    return result


def verify_paydunya_hash(payload: dict) -> None:
    """Compare `data.hash` au SHA-512 de PAYDUNYA_MASTER_KEY."""
    master_key = os.environ.get("PAYDUNYA_MASTER_KEY", "").strip()
    settings = get_settings()
    if not master_key:
        if settings.is_production:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="PAYDUNYA_MASTER_KEY non configurée : webhook désactivé en production",
            )
        return

    data = payload.get("data") if isinstance(payload, dict) else None
    provided = data.get("hash", "") if isinstance(data, dict) else ""
    expected = hashlib.sha512(master_key.encode("utf-8")).hexdigest()
    if not provided or not hmac.compare_digest(str(provided).lower(), expected.lower()):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Hash PayDunya invalide")
