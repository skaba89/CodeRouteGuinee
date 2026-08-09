"""Privacy helpers P11 pour les logs, traces et exports SOC.

Les identifiants opérationnels restent disponibles dans PostgreSQL selon RBAC,
mais ne quittent pas l'application en clair vers stdout/SIEM/OTLP.
"""
from __future__ import annotations

import hashlib
import hmac
import ipaddress
import logging
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
    "email": "email",
    "phone": "phone",
    "telephone": "phone",
    "identity_number": "identity",
    "nni": "identity",
    "ip": "ip",
    "client_ip": "ip",
}
_SECRET_KEYS = {
    "password", "passwd", "pwd", "token", "access_token", "refresh_token",
    "csrf_token", "secret", "secret_key", "api_key", "authorization", "cookie",
    "client_secret", "private_key", "pin", "cvv",
}
_OPAQUE_KEYS = {"url", "query", "query_string", "body", "request_body", "form_data"}
_UUID_RE = re.compile(r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-5][0-9a-fA-F]{3}-[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}\b")
_IPV4_RE = re.compile(r"(?<![\d.])(?:\d{1,3}\.){3}\d{1,3}(?![\d.])")
_EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")


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
    lowered = key.lower()
    if lowered in _SECRET_KEYS or lowered in _OPAQUE_KEYS:
        return _REDACTED
    namespace = _PSEUDONYM_KEYS.get(lowered)
    if namespace is None:
        return value
    return pseudonymize_ip(value) if namespace == "ip" else pseudonymize(value, namespace)


def sanitize_free_text(text: str) -> str:
    """Supprime UUID/IP/email bruts qui auraient échappé aux champs structurés."""
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

    def _email(match: re.Match[str]) -> str:
        return pseudonymize(match.group(0).lower(), "email")

    text = _UUID_RE.sub(_uuid, text)
    text = _IPV4_RE.sub(_ip, text)
    return _EMAIL_RE.sub(_email, text)


def _sanitize_nested(key: str, value: object) -> object:
    direct = sanitize_identifier_field(key, value)
    if direct is not value:
        return direct
    if isinstance(value, str):
        return sanitize_free_text(value)
    if isinstance(value, dict):
        return {str(k): _sanitize_nested(str(k), v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_sanitize_nested(key, item) for item in value]
    return value


def sanitize_context(context: dict | None) -> dict:
    if not isinstance(context, dict):
        return {}
    return {str(key): _sanitize_nested(str(key), value) for key, value in context.items()}


def _inject_trace_context(record: logging.LogRecord) -> None:
    try:
        from opentelemetry import trace
        context = trace.get_current_span().get_span_context()
        if context and context.is_valid:
            record.trace_id = f"{context.trace_id:032x}"
            record.span_id = f"{context.span_id:016x}"
    except Exception:
        return


class SOCPrivacyFilter(logging.Filter):
    """Dernière barrière avant stdout/SIEM : pseudonymise IDs et IP partout."""

    def filter(self, record: logging.LogRecord) -> bool:
        try:
            record.msg = sanitize_free_text(record.getMessage())
            record.args = ()
        except Exception:
            pass
        for key, value in list(record.__dict__.items()):
            if key.startswith("_") or key in {"msg", "args"}:
                continue
            try:
                record.__dict__[key] = _sanitize_nested(key, value)
            except Exception:
                pass
        _inject_trace_context(record)
        return True


def safe_actor_ref(actor_id: object) -> str | None:
    if actor_id in (None, ""):
        return None
    return pseudonymize(actor_id, "actor")
