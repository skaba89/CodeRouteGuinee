"""Privacy helpers P11 pour les logs, traces et exports SOC.

Les identifiants opérationnels restent disponibles dans PostgreSQL selon RBAC,
mais ne quittent pas l'application en clair vers stdout/SIEM/OTLP.
"""
from __future__ import annotations

import hashlib
import hmac
import ipaddress
import re

from app.soc_config import get_soc_settings

_REDACTED = "***REDACTED***"
_PSEUDONYM_KEYS = {
    "user_id": "usr",
    "candidate_id": "cand",
    "attempt_id": "attempt",
    "session_id": "session",
    "payment_id": "payment",
    "actor_id": "actor",
    "entity_id": "entity",
    "device_session_id": "device",
    "ip": "ip",
    "client_ip": "ip",
}
_UUID_RE = re.compile(r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-5][0-9a-fA-F]{3}-[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}\b")
_IPV4_RE = re.compile(r"(?<![\d.])(?:\d{1,3}\.){3}\d{1,3}(?![\d.])")


def pseudonymize(value: object, namespace: str) -> str:
    raw = str(value or "").strip()
    if not raw:
        return _REDACTED
    key = get_soc_settings().pseudonym_key.encode("utf-8")
    if not key:
        return _REDACTED
    digest = hmac.new(key, f"{namespace}\0{raw}".encode("utf-8"), hashlib.sha256).hexdigest()[:20]
    return f"{namespace}:{digest}"


def pseudonymize_ip(value: object) -> str:
    raw = str(value or "").strip()
    try:
        canonical = str(ipaddress.ip_address(raw))
    except ValueError:
        canonical = raw
    return pseudonymize(canonical, "ip")


def sanitize_identifier_field(key: str, value: object) -> object:
    namespace = _PSEUDONYM_KEYS.get(key.lower())
    if namespace is None:
        return value
    return pseudonymize_ip(value) if namespace == "ip" else pseudonymize(value, namespace)


def sanitize_free_text(text: str) -> str:
    """Supprime UUID/IP bruts qui auraient échappé aux champs structurés."""
    if not text:
        return text

    def _uuid(match: re.Match[str]) -> str:
        return pseudonymize(match.group(0), "uuid")

    def _ip(match: re.Match[str]) -> str:
        value = match.group(0)
        try:
            ipaddress.ip_address(value)
        except ValueError:
            return value
        return pseudonymize_ip(value)

    text = _UUID_RE.sub(_uuid, text)
    return _IPV4_RE.sub(_ip, text)


def safe_actor_ref(actor_id: object) -> str | None:
    if actor_id in (None, ""):
        return None
    return pseudonymize(actor_id, "actor")
