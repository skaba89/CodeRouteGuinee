from __future__ import annotations

import os
from uuid import uuid4

from fastapi.testclient import TestClient

from app.db.session import init_db
from app.main import app


os.environ.setdefault("EDGE_LEASE_SIGNING_SECRET", "coderoute-p9-fallback-signing-secret-at-least-32-characters")


def _super_admin_headers(client: TestClient) -> dict[str, str]:
    suffix = uuid4().hex
    email = f"p9-super-{suffix}@coderoute.local"
    password = "P9SupplyChainAdmin123!"
    register = client.post(
        "/api/v1/auth/register",
        json={"email": email, "full_name": "P9 Supply Chain", "password": password, "role": "super_admin"},
    )
    assert register.status_code == 201, register.text
    login = client.post("/api/v1/auth/login", data={"username": email, "password": password})
    assert login.status_code == 200, login.text
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def _create_release(client: TestClient, headers: dict[str, str], sha: str = "a" * 64) -> dict:
    response = client.post(
        "/api/v1/center-edge/releases",
        headers=headers,
        json={
            "software_version": "edge-agent-0.4.0",
            "artifact_url": "https://releases.coderoute.gov.gn/edge-agent-0.4.0.tar.gz",
            "artifact_sha256": sha,
            "artifact_size_bytes": 456789,
            "min_current_version": "edge-agent-0.3.0",
            "release_notes": "P9 supply chain test",
            "canary_node_ids": ["node-p9-fake-canary"],
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def _rollout_canary(client: TestClient, headers: dict[str, str], release_id: str):
    return client.post(
        f"/api/v1/center-edge/releases/{release_id}/rollout",
        headers=headers,
        json={
            "rollout_status": "canary",
            "rollout_percent": 0,
            "canary_node_ids": ["node-p9-fake-canary"],
            "reason": "Canary de validation P9",
        },
    )


def _evidence(artifact_sha: str, *, scan_status: str = "passed") -> dict:
    return {
        "builder": "github-actions",
        "source_commit_sha": "1" * 40,
        "workflow_ref": "Edge Release Supply Chain@refs/tags/edge-agent-0.4.0",
        "provenance_url": "https://github.com/skaba89/CodeRouteGuinee/attestations/1001",
        "sbom_sha256": "b" * 64,
        "sbom_attestation_url": "https://github.com/skaba89/CodeRouteGuinee/attestations/1002",
        "subject_sha256": artifact_sha,
        "vulnerability_scan_status": scan_status,
    }


def test_rollout_is_blocked_until_supply_chain_evidence_is_signed() -> None:
    init_db()
    with TestClient(app) as client:
        headers = _super_admin_headers(client)
        release = _create_release(client, headers)
        release_id = release["release_id"]

        blocked = _rollout_canary(client, headers, release_id)
        assert blocked.status_code == 409, blocked.text
        assert blocked.json()["detail"]["code"] == "EDGE_SUPPLY_CHAIN_EVIDENCE_REQUIRED"

        attached = client.post(
            f"/api/v1/center-edge/releases/{release_id}/supply-chain",
            headers=headers,
            json=_evidence("a" * 64),
        )
        assert attached.status_code == 200, attached.text
        body = attached.json()
        assert body["supply_chain_ready"] is True
        assert body["manifest"]["version"] == 2
        assert body["manifest"]["supply_chain"]["subject_sha256"] == "a" * 64
        assert body["manifest"]["supply_chain"]["vulnerability_scan_status"] == "passed"

        # P9 laisse maintenant passer vers le garde P8 ; le fake canary n'est
        # volontairement pas enrôlé, donc on doit obtenir l'erreur P8 suivante.
        p8_guard = _rollout_canary(client, headers, release_id)
        assert p8_guard.status_code == 409, p8_guard.text
        assert p8_guard.json()["detail"]["code"] == "EDGE_CANARY_NOT_READY"


def test_failed_vulnerability_scan_never_becomes_rollout_ready() -> None:
    init_db()
    with TestClient(app) as client:
        headers = _super_admin_headers(client)
        release = _create_release(client, headers, sha="c" * 64)
        release_id = release["release_id"]

        attached = client.post(
            f"/api/v1/center-edge/releases/{release_id}/supply-chain",
            headers=headers,
            json=_evidence("c" * 64, scan_status="failed"),
        )
        assert attached.status_code == 200, attached.text
        assert attached.json()["supply_chain_ready"] is False

        blocked = _rollout_canary(client, headers, release_id)
        assert blocked.status_code == 409, blocked.text
        assert blocked.json()["detail"]["code"] == "EDGE_SUPPLY_CHAIN_EVIDENCE_REQUIRED"


def test_supply_chain_subject_digest_must_match_release_artifact() -> None:
    init_db()
    with TestClient(app) as client:
        headers = _super_admin_headers(client)
        release = _create_release(client, headers, sha="d" * 64)
        response = client.post(
            f"/api/v1/center-edge/releases/{release['release_id']}/supply-chain",
            headers=headers,
            json=_evidence("e" * 64),
        )
        assert response.status_code == 422
        assert "digest" in response.text.lower()


def test_release_signing_endpoint_exposes_active_and_previous_rotation_keys(monkeypatch) -> None:
    active = "p9-active-release-signing-secret-abcdefghijklmnopqrstuvwxyz"
    previous = "p9-previous-release-signing-secret-abcdefghijklmnopqrstuvwxyz"
    monkeypatch.setenv("EDGE_RELEASE_SIGNING_SECRET", active)
    monkeypatch.setenv("EDGE_RELEASE_PREVIOUS_SIGNING_SECRETS", previous)

    with TestClient(app) as client:
        response = client.get("/api/v1/center-edge/release-signing-key")
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["algorithm"] == "Ed25519"
        assert body["key_id"] == body["trusted_keys"][0]["key_id"]
        assert body["trusted_keys"][0]["active"] is True
        assert len(body["trusted_keys"]) == 2
        assert body["trusted_keys"][0]["key_id"] != body["trusted_keys"][1]["key_id"]
        assert body["trusted_keys"][1]["active"] is False
