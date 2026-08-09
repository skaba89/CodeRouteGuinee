from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db.session import SessionLocal, init_db
from app.main import app
from app.models_audit import AuditLog
from app.routers import reliability as reliability_router


class FakeReliabilitySettings:
    evidence_enabled = True
    evidence_token = "evidence-token-" + ("x" * 40)

    def safe_policy(self):
        return {
            "slo": {"availability_percent": 99.9, "p95_latency_ms": 1000, "max_5xx_percent": 1.0},
            "dr": {"rpo_minutes": 5, "rto_minutes": 30, "bucket_configured": True},
            "observability": {"metrics_enabled": True, "reliability_evidence_enabled": True},
        }


def _settings() -> FakeReliabilitySettings:
    return FakeReliabilitySettings()


def test_machine_evidence_requires_dedicated_token(monkeypatch) -> None:
    monkeypatch.setattr(reliability_router, "get_reliability_settings", _settings)
    init_db()
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/operations/reliability/evidence",
            json={"kind": "backup_uploaded", "occurred_at": datetime.now(UTC).isoformat()},
        )
    assert response.status_code == 401


def test_valid_backup_evidence_is_audited_without_actor(monkeypatch) -> None:
    monkeypatch.setattr(reliability_router, "get_reliability_settings", _settings)
    init_db()
    artifact = "a" * 64
    occurred = datetime.now(UTC) - timedelta(seconds=5)

    db = SessionLocal()
    try:
        before = len(list(db.scalars(select(AuditLog).where(AuditLog.action == "reliability.backup_uploaded")).all()))
    finally:
        db.close()

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/operations/reliability/evidence",
            headers={"X-Reliability-Evidence-Token": _settings().evidence_token},
            json={
                "kind": "backup_uploaded",
                "occurred_at": occurred.isoformat(),
                "artifact_sha256": artifact,
                "region": "paris",
                "reference": "coderoute/production/2026/08/backup.crgbak",
            },
        )
    assert response.status_code == 201, response.text

    db = SessionLocal()
    try:
        rows = list(db.scalars(select(AuditLog).where(AuditLog.action == "reliability.backup_uploaded")).all())
        assert len(rows) == before + 1
        event = rows[-1]
        assert event.actor_id is None
        assert event.details["artifact_sha256"] == artifact
        assert event.details["region"] == "paris"
        assert "token" not in str(event.details).lower()
    finally:
        db.close()


def test_evidence_reference_rejects_urls_or_credentials(monkeypatch) -> None:
    monkeypatch.setattr(reliability_router, "get_reliability_settings", _settings)
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/operations/reliability/evidence",
            headers={"X-Reliability-Evidence-Token": _settings().evidence_token},
            json={
                "kind": "backup_uploaded",
                "occurred_at": datetime.now(UTC).isoformat(),
                "reference": "https://user:secret@objects.example/backup.crgbak",
            },
        )
    assert response.status_code == 422


def test_evidence_allows_small_clock_skew_but_rejects_large_future_skew(monkeypatch) -> None:
    monkeypatch.setattr(reliability_router, "get_reliability_settings", _settings)
    token = _settings().evidence_token
    with TestClient(app) as client:
        accepted = client.post(
            "/api/v1/operations/reliability/evidence",
            headers={"X-Reliability-Evidence-Token": token},
            json={
                "kind": "ha_failover_probe_passed",
                "occurred_at": (datetime.now(UTC) + timedelta(minutes=2)).isoformat(),
                "availability_percent": 100.0,
                "duration_seconds": 120,
            },
        )
        rejected = client.post(
            "/api/v1/operations/reliability/evidence",
            headers={"X-Reliability-Evidence-Token": token},
            json={
                "kind": "ha_failover_probe_passed",
                "occurred_at": (datetime.now(UTC) + timedelta(minutes=10)).isoformat(),
                "availability_percent": 100.0,
                "duration_seconds": 120,
            },
        )
    assert accepted.status_code == 201
    assert rejected.status_code == 422
