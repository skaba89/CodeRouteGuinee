"""Configuration P11 — SOC, télémétrie et intégrité d'audit.

Les paramètres SOC sont séparés des règles métier. Les exporters externes sont
best-effort afin qu'une panne SIEM/OTLP ne puisse jamais interrompre un examen.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from urllib.parse import urlparse


def _bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except ValueError:
        return default


def _int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


@dataclass(frozen=True)
class SOCSettings:
    enabled: bool
    pseudonym_key: str
    audit_chain_enabled: bool
    audit_chain_hmac_key: str
    audit_verify_interval_seconds: int
    otel_traces_enabled: bool
    otel_endpoint: str
    otel_headers: str
    otel_service_name: str
    otel_sample_ratio: float
    waf_required: bool
    waf_provider: str
    siem_required: bool

    def safe_policy(self) -> dict:
        return {
            "enabled": self.enabled,
            "audit_chain_enabled": self.audit_chain_enabled,
            "audit_verify_interval_seconds": self.audit_verify_interval_seconds,
            "otel": {
                "traces_enabled": self.otel_traces_enabled,
                "endpoint_configured": bool(self.otel_endpoint),
                "service_name": self.otel_service_name,
                "sample_ratio": self.otel_sample_ratio,
            },
            "waf": {"required": self.waf_required, "provider": self.waf_provider or None},
            "siem": {"required": self.siem_required},
        }

    def validate(self, *, production: bool) -> None:
        errors: list[str] = []
        if not 0.0 <= self.otel_sample_ratio <= 1.0:
            errors.append("OTEL_SAMPLE_RATIO doit être compris entre 0 et 1")
        if not 60 <= self.audit_verify_interval_seconds <= 86_400:
            errors.append("AUDIT_VERIFY_INTERVAL_SECONDS doit être compris entre 60 et 86400")

        if production and self.enabled and len(self.pseudonym_key) < 32:
            errors.append("SOC_PSEUDONYM_KEY doit contenir au moins 32 caractères")
        if production and self.audit_chain_enabled and len(self.audit_chain_hmac_key) < 32:
            errors.append("AUDIT_CHAIN_HMAC_KEY doit contenir au moins 32 caractères")

        if self.otel_traces_enabled:
            if not self.otel_endpoint:
                errors.append("OTEL_EXPORTER_OTLP_ENDPOINT est obligatoire lorsque OTEL_TRACES_ENABLED=true")
            else:
                parsed = urlparse(self.otel_endpoint)
                if production and parsed.scheme != "https":
                    errors.append("OTEL_EXPORTER_OTLP_ENDPOINT doit utiliser HTTPS en production")
                if parsed.username or parsed.password:
                    errors.append("OTEL_EXPORTER_OTLP_ENDPOINT ne doit contenir aucun credential")

        if production and self.waf_required and not self.waf_provider:
            errors.append("WAF_PROVIDER doit être défini lorsque WAF_REQUIRED=true")

        if errors:
            raise RuntimeError("Configuration SOC P11 invalide:\n" + "\n".join(f"  ❌ {item}" for item in errors))


@lru_cache(maxsize=1)
def get_soc_settings() -> SOCSettings:
    return SOCSettings(
        enabled=_bool("SOC_ENABLED", False),
        pseudonym_key=os.getenv("SOC_PSEUDONYM_KEY", "").strip(),
        audit_chain_enabled=_bool("AUDIT_CHAIN_ENABLED", False),
        audit_chain_hmac_key=os.getenv("AUDIT_CHAIN_HMAC_KEY", "").strip(),
        audit_verify_interval_seconds=_int("AUDIT_VERIFY_INTERVAL_SECONDS", 900),
        otel_traces_enabled=_bool("OTEL_TRACES_ENABLED", False),
        otel_endpoint=os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "").strip(),
        otel_headers=os.getenv("OTEL_EXPORTER_OTLP_HEADERS", "").strip(),
        otel_service_name=os.getenv("OTEL_SERVICE_NAME", "coderoute-api").strip() or "coderoute-api",
        otel_sample_ratio=_float("OTEL_SAMPLE_RATIO", 0.05),
        waf_required=_bool("WAF_REQUIRED", False),
        waf_provider=os.getenv("WAF_PROVIDER", "").strip(),
        siem_required=_bool("SIEM_REQUIRED", False),
    )
