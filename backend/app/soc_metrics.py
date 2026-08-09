from __future__ import annotations

from datetime import UTC, datetime

from prometheus_client import Counter, Gauge

SECURITY_EVENTS_TOTAL = Counter(
    "coderoute_security_events_total",
    "Événements SOC HTTP agrégés sans identifiant citoyen.",
    ("kind",),
)
AUDIT_CHAIN_VALID = Gauge(
    "coderoute_audit_chain_valid",
    "Résultat de la dernière vérification HMAC du journal: 1=valide, 0=invalide.",
    multiprocess_mode="livemin",
)
AUDIT_CHAIN_LAST_VERIFY = Gauge(
    "coderoute_audit_chain_last_verify_timestamp_seconds",
    "Horodatage de la dernière vérification du journal d'audit.",
    multiprocess_mode="livemax",
)

_ALLOWED_SECURITY_EVENTS = {"access_denied", "rate_limited", "server_error"}


def record_security_event(kind: str) -> None:
    if kind in _ALLOWED_SECURITY_EVENTS:
        SECURITY_EVENTS_TOTAL.labels(kind=kind).inc()


def record_audit_chain_check(valid: bool, occurred_at: datetime | None = None) -> None:
    when = occurred_at or datetime.now(UTC)
    if when.tzinfo is None:
        when = when.replace(tzinfo=UTC)
    AUDIT_CHAIN_VALID.set(1.0 if valid else 0.0)
    AUDIT_CHAIN_LAST_VERIFY.set(when.timestamp())
