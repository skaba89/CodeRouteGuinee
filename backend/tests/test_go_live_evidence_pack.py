from __future__ import annotations

from datetime import UTC, datetime

from scripts.collect_go_live_evidence import (
    _safe_base_url,
    _sanitize,
    evaluate_snapshot,
    render_markdown,
)


def _obs(body=None, *, ok=True, skipped=False):
    return {
        "ok": ok,
        "skipped": skipped,
        "status_code": 200 if ok else None,
        "error": None if ok else "test",
        "body": body,
    }


def test_base_url_rejects_credentials_query_and_plain_http_remote():
    for value in (
        "http://example.org",
        "https://user:pass@example.org",
        "https://example.org?token=secret",
        "https://example.org/api",
    ):
        try:
            _safe_base_url(value, allow_http=False)
        except ValueError:
            pass
        else:
            raise AssertionError(f"URL should have been rejected: {value}")

    assert _safe_base_url("https://example.org/", allow_http=False) == "https://example.org"
    assert _safe_base_url("http://localhost:8000", allow_http=False) == "http://localhost:8000"


def test_sanitize_redacts_credentials_emails_and_url_queries():
    value = {
        "access_token": "super-secret-token",
        "nested": {
            "message": "Bearer abc.def.ghi for citizen@example.org",
            "reference": "https://example.org/path?token=leak#fragment",
        },
    }
    safe = _sanitize(value)
    assert safe["access_token"] == "[REDACTED]"
    assert "abc.def.ghi" not in safe["nested"]["message"]
    assert "citizen@example.org" not in safe["nested"]["message"]
    assert "token=leak" not in safe["nested"]["reference"]
    assert "#fragment" not in safe["nested"]["reference"]


def test_evaluate_snapshot_passes_only_automatable_checks_and_never_claims_homologation():
    now = datetime(2026, 8, 9, 18, 30, tzinfo=UTC)
    evidence_time = now.isoformat()
    observations = {
        "health_live": _obs({"status": "ok", "runtime": {"deployment_id": "production"}}),
        "health_readiness": _obs({"status": "ready", "blocking_checks": []}),
        "reliability": _obs(
            {
                "last_evidence": {
                    "backup_uploaded": evidence_time,
                    "restore_drill_passed": evidence_time,
                    "ha_failover_probe_passed": evidence_time,
                }
            }
        ),
        "security": _obs(
            {
                "status": "ok",
                "soc_policy": {"enabled": True, "audit_chain_enabled": True},
                "audit_chain": {"valid": True},
                "alerts": [],
            }
        ),
        "governance_contract": _obs({"alignment": {"aligned": True}}),
        "governance_readiness": _obs({"go_live_allowed": True, "blockers": []}),
        "homologation_dossiers": _obs([]),
    }

    result = evaluate_snapshot(
        observations,
        now=now,
        expected_deployment_id="production",
    )
    assert result["status"] == "automated_checks_passed"
    assert result["automated_checks_passed"] is True
    assert result["blockers"] == []
    assert result["institutional_homologation_claimed"] is False
    assert result["manual_evidence_required"]

    markdown = render_markdown(
        {
            "schema": "coderoute_go_live_evidence_pack_v1",
            "generated_at": now.isoformat(),
            "target_origin": "https://example.org",
            "assessment": result,
        }
    )
    assert "Homologation institutionnelle déclarée par cet outil: **NON**" in markdown
    assert "Preuves humaines / externes toujours requises" in markdown


def test_missing_authenticated_access_remains_a_blocker():
    now = datetime(2026, 8, 9, 18, 30, tzinfo=UTC)
    skipped = _obs(None, ok=False, skipped=True)
    observations = {
        "health_live": _obs({"status": "ok", "runtime": {"deployment_id": "production"}}),
        "health_readiness": _obs({"status": "ready"}),
        "reliability": skipped,
        "security": skipped,
        "governance_contract": skipped,
        "governance_readiness": skipped,
        "homologation_dossiers": skipped,
    }
    result = evaluate_snapshot(observations, now=now)
    assert result["status"] == "blocked"
    assert result["institutional_homologation_claimed"] is False
    assert any("AUTHENTICATED_EVIDENCE_MISSING" in item for item in result["blockers"])


def test_stale_reliability_evidence_blocks_readiness():
    now = datetime(2026, 8, 9, 18, 30, tzinfo=UTC)
    observations = {
        "health_live": _obs({"status": "ok"}),
        "health_readiness": _obs({"status": "ready"}),
        "reliability": _obs(
            {
                "last_evidence": {
                    "backup_uploaded": "2026-08-01T00:00:00+00:00",
                    "restore_drill_passed": "2026-01-01T00:00:00+00:00",
                    "ha_failover_probe_passed": "2026-01-01T00:00:00+00:00",
                }
            }
        ),
        "security": _obs(
            {
                "status": "ok",
                "soc_policy": {"enabled": True, "audit_chain_enabled": True},
                "audit_chain": {"valid": True},
            }
        ),
        "governance_contract": _obs({"alignment": {"aligned": True}}),
        "governance_readiness": _obs({"go_live_allowed": True}),
        "homologation_dossiers": _obs([]),
    }
    result = evaluate_snapshot(observations, now=now)
    assert result["status"] == "blocked"
    codes = {item["code"] for item in result["checks"] if not item["passed"]}
    assert "P10_BACKUP_FRESH" in codes
    assert "P10_RESTORE_DRILL_FRESH" in codes
    assert "P10_FAILOVER_FRESH" in codes
