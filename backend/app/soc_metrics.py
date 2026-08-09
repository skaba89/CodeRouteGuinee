from __future__ import annotations

from datetime import UTC, datetime

from prometheus_client import Counter, Gauge

SECURITY_EVENTS_TOTAL = Counter(
    "coderoute_security_events_total",
    "Événements SOC HTTP agrégés sans identifiant citoyen.",
    ("kind",),
)
SOC_ENABLED = Gauge(
    "coderoute_soc_enabled",
    "État d'activation du SOC applicatif: 1=activé, 0=dormant.",
    multiprocess_mode="livemostrecent",
)
SOC_AUDIT_EXPECTED = Gauge(
    "coderoute_soc_audit_expected",
    "La chaîne d'audit HMAC doit-elle être présente: 1=oui, 0=non.",
    multiprocess_mode="livemostrecent",
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


def record_soc_policy_state(*, enabled: bool, audit_chain_enabled: bool) -> None:
    SOC_ENABLED.set(1.0 if enabled else 0.0)
    SOC_AUDIT_EXPECTED.set(1.0 if enabled and audit_chain_enabled else 0.0)


def record_security_event(kind: str) -> None:
    if kind in _ALLOWED_SECURITY_EVENTS:
        SECURITY_EVENTS_TOTAL.labels(kind=kind).inc()


def record_audit_chain_check(valid: bool, occurred_at: datetime | None = None) -> None:
    when = occurred_at or datetime.now(UTC)
    if when.tzinfo is None:
        when = when.replace(tzinfo=UTC)
    AUDIT_CHAIN_VALID.set(1.0 if valid else 0.0)
    AUDIT_CHAIN_LAST_VERIFY.set(when.timestamp())
