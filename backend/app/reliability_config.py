"""Configuration P10.2 — observabilité, SLO et politique PRA.

L'API ne charge volontairement aucune clé AES ni credential S3. Ces secrets
appartiennent exclusivement au service cron de sauvegarde. Le backend connaît
uniquement la politique et les identifiants non secrets nécessaires au pilotage.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache


def _bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


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
class ReliabilitySettings:
    metrics_enabled: bool
    metrics_token: str
    evidence_enabled: bool
    evidence_token: str
    slo_availability_percent: float
    slo_p95_latency_ms: int
    slo_max_5xx_percent: float
    dr_rpo_minutes: int
    dr_rto_minutes: int
    backup_required: bool
    backup_s3_bucket: str
    backup_s3_prefix: str
    backup_primary_region: str
    backup_target_region: str
    backup_require_off_region: bool
    backup_encryption_key_id: str

    def safe_policy(self) -> dict:
        return {
            "slo": {
                "availability_percent": self.slo_availability_percent,
                "p95_latency_ms": self.slo_p95_latency_ms,
                "max_5xx_percent": self.slo_max_5xx_percent,
            },
            "dr": {
                "rpo_minutes": self.dr_rpo_minutes,
                "rto_minutes": self.dr_rto_minutes,
                "backup_required": self.backup_required,
                "off_region_required": self.backup_require_off_region,
                "primary_region": self.backup_primary_region or None,
                "target_region": self.backup_target_region or None,
                "bucket_configured": bool(self.backup_s3_bucket),
                "encryption_key_id": self.backup_encryption_key_id or None,
            },
            "observability": {
                "metrics_enabled": self.metrics_enabled,
                "reliability_evidence_enabled": self.evidence_enabled,
            },
        }

    def validate(self, *, production: bool) -> None:
        errors: list[str] = []

        if not (99.0 <= self.slo_availability_percent <= 100.0):
            errors.append("SLO_AVAILABILITY_PERCENT doit être compris entre 99 et 100")
        if not (50 <= self.slo_p95_latency_ms <= 60_000):
            errors.append("SLO_P95_LATENCY_MS doit être compris entre 50 et 60000")
        if not (0.0 <= self.slo_max_5xx_percent <= 10.0):
            errors.append("SLO_MAX_5XX_PERCENT doit être compris entre 0 et 10")
        if self.dr_rpo_minutes <= 0 or self.dr_rto_minutes <= 0:
            errors.append("DR_RPO_MINUTES et DR_RTO_MINUTES doivent être > 0")

        if production and self.metrics_enabled and len(self.metrics_token) < 32:
            errors.append("METRICS_TOKEN doit contenir au moins 32 caractères en production")
        if production and self.evidence_enabled and len(self.evidence_token) < 32:
            errors.append("RELIABILITY_EVIDENCE_TOKEN doit contenir au moins 32 caractères en production")

        if self.backup_required:
            if not self.backup_s3_bucket:
                errors.append("BACKUP_S3_BUCKET est obligatoire lorsque BACKUP_REQUIRED=true")
            if not self.backup_target_region:
                errors.append("BACKUP_TARGET_REGION est obligatoire lorsque BACKUP_REQUIRED=true")
            if not self.backup_encryption_key_id:
                errors.append("BACKUP_ENCRYPTION_KEY_ID est obligatoire lorsque BACKUP_REQUIRED=true")
            if self.backup_require_off_region:
                if not self.backup_primary_region:
                    errors.append("BACKUP_PRIMARY_REGION est obligatoire pour la règle hors région")
                elif self.backup_primary_region.strip().lower() == self.backup_target_region.strip().lower():
                    errors.append("BACKUP_TARGET_REGION doit être différente de BACKUP_PRIMARY_REGION")

        if errors:
            raise RuntimeError("Configuration reliability/PRA invalide:\n" + "\n".join(f"  ❌ {e}" for e in errors))


@lru_cache(maxsize=1)
def get_reliability_settings() -> ReliabilitySettings:
    return ReliabilitySettings(
        metrics_enabled=_bool("METRICS_ENABLED", False),
        metrics_token=os.getenv("METRICS_TOKEN", "").strip(),
        evidence_enabled=_bool("RELIABILITY_EVIDENCE_ENABLED", False),
        evidence_token=os.getenv("RELIABILITY_EVIDENCE_TOKEN", "").strip(),
        slo_availability_percent=_float("SLO_AVAILABILITY_PERCENT", 99.9),
        slo_p95_latency_ms=_int("SLO_P95_LATENCY_MS", 1000),
        slo_max_5xx_percent=_float("SLO_MAX_5XX_PERCENT", 1.0),
        dr_rpo_minutes=_int("DR_RPO_MINUTES", 5),
        dr_rto_minutes=_int("DR_RTO_MINUTES", 30),
        backup_required=_bool("BACKUP_REQUIRED", False),
        backup_s3_bucket=os.getenv("BACKUP_S3_BUCKET", "").strip(),
        backup_s3_prefix=os.getenv("BACKUP_S3_PREFIX", "coderoute/production").strip("/"),
        backup_primary_region=os.getenv("BACKUP_PRIMARY_REGION", "").strip(),
        backup_target_region=os.getenv("BACKUP_TARGET_REGION", "").strip(),
        backup_require_off_region=_bool("BACKUP_REQUIRE_OFF_REGION", True),
        backup_encryption_key_id=os.getenv("BACKUP_ENCRYPTION_KEY_ID", "").strip(),
    )
