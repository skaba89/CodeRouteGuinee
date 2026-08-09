from __future__ import annotations

import base64
import os
from datetime import UTC, datetime
from uuid import uuid4

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from fastapi.testclient import TestClient

from app.db.session import SessionLocal, init_db
from app.edge_gateway import (
    EDGE_REQUIRED_CAPABILITIES,
    EDGE_TARGET_SOFTWARE_VERSION,
    canonical_edge_payload,
    heartbeat_signing_payload,
    iso_z,
)
from app.edge_offline import machine_action_payload
from app.edge_release import verify_release_manifest
from app.main import app
from app.models_center import Center


os.environ.setdefault("EDGE_LEASE_SIGNING_SECRET", "coderoute-release-test-secret-at-least-32-characters")


def _b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _sign(private_key: Ed25519PrivateKey, payload: dict) -> str:
    return _b64url(private_key.sign(canonical_edge_payload(payload)))


def _super_admin_headers(client: TestClient) -> dict[str, str]:
    suffix = uuid4().hex
    email = f"release-super-{suffix}@coderoute.local"
    password = "ReleaseSuperAdmin123!"
    register = client.post(
        "/api/v1/auth/register",
        json={"email": email, "full_name": "Super Admin Release", "password": password, "role": "super_admin"},
    )
    assert register.status_code == 201, register.text
    login = client.post("/api/v1/auth/login", data={"username": email, "password": password})
    assert login.status_code == 200, login.text
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def _center() -> Center:
    suffix = uuid4().hex[:10].upper()
    center = Center(
        code=f"REL-{suffix}",
        name="Centre Release Canary",
        city="Conakry",
        address="Lab national Edge",
        capacity=30,
        status="accredited",
    )
    with SessionLocal() as db:
        db.add(center)
        db.commit()
        db.refresh(center)
        db.expunge(center)
    return center


def _enroll(client: TestClient, headers: dict[str, str], center: Center, private_key: Ed25519PrivateKey) -> dict:
    public_raw = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    response = client.post(
        "/api/v1/center-edge/nodes",
        headers=headers,
        json={
            "center_id": center.id,
            "label": "Gateway Release Canary",
            "public_key_b64": _b64url(public_raw),
            "capabilities": list(EDGE_REQUIRED_CAPABILITIES),
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def _heartbeat(private_key: Ed25519PrivateKey, *, node_id: str, center_id: str, sequence: int) -> dict:
    sent_at = datetime.now(UTC).replace(microsecond=0)
    signed = heartbeat_signing_payload(
        node_id=node_id,
        center_id=center_id,
        sequence=sequence,
        sent_at=sent_at,
        software_version=EDGE_TARGET_SOFTWARE_VERSION,
        capabilities=list(EDGE_REQUIRED_CAPABILITIES),
        telemetry={
            "active_leases": 0,
            "finalized_leases": 0,
            "synced_leases": 0,
            "sync_pending": 0,
            "revalidation_required": 0,
            "corrupt_leases": 0,
            "media_files": 0,
            "media_bytes": 0,
        },
    )
    return {**signed, "signature_b64": _sign(private_key, signed)}


def _machine(
    private_key: Ed25519PrivateKey,
    *,
    action: str,
    node_id: str,
    center_id: str,
    sequence: int,
    fields: dict,
) -> dict:
    sent_at = datetime.now(UTC).replace(microsecond=0)
    signed = machine_action_payload(
        action=action,
        node_id=node_id,
        center_id=center_id,
        sequence=sequence,
        sent_at=iso_z(sent_at),
        fields=fields,
    )
    return {
        "node_id": node_id,
        "center_id": center_id,
        "sequence": sequence,
        "sent_at": iso_z(sent_at),
        **fields,
        "signature_b64": _sign(private_key, signed),
    }


def _create_release(
    client: TestClient,
    headers: dict[str, str],
    *,
    version: str,
    sha: str,
    rollback_release_id: str | None = None,
) -> dict:
    response = client.post(
        "/api/v1/center-edge/releases",
        headers=headers,
        json={
            "software_version": version,
            "artifact_url": f"https://releases.coderoute.gov.gn/{version}.tar.gz",
            "artifact_sha256": sha,
            "artifact_size_bytes": 12345,
            "min_current_version": "edge-agent-0.2.0",
            "release_notes": f"Release de test {version}",
            "rollback_release_id": rollback_release_id,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def _rollout(client: TestClient, headers: dict[str, str], release_id: str, status_value: str, percent: int, **extra) -> object:
    return client.post(
        f"/api/v1/center-edge/releases/{release_id}/rollout",
        headers=headers,
        json={
            "rollout_status": status_value,
            "rollout_percent": percent,
            "reason": f"Test transition {status_value}",
            **extra,
        },
    )


def _attest(
    client: TestClient,
    private_key: Ed25519PrivateKey,
    *,
    node_id: str,
    center_id: str,
    sequence: int,
    release_id: str,
    version: str,
    result: str,
    sha: str,
):
    fields = {
        "release_id": release_id,
        "software_version": version,
        "result": result,
        "artifact_sha256": sha,
    }
    return client.post(
        "/api/v1/center-edge/release/attest",
        json=_machine(
            private_key,
            action="release.attest",
            node_id=node_id,
            center_id=center_id,
            sequence=sequence,
            fields=fields,
        ),
    )


def test_release_quality_gate_auto_pause_and_rollback() -> None:
    init_db()
    private_key = Ed25519PrivateKey.generate()

    with TestClient(app) as client:
        headers = _super_admin_headers(client)
        center = _center()
        node = _enroll(client, headers, center, private_key)
        heartbeat = client.post(
            "/api/v1/center-edge/heartbeat",
            json=_heartbeat(private_key, node_id=node["node_id"], center_id=center.id, sequence=1),
        )
        assert heartbeat.status_code == 200, heartbeat.text

        # Construire une version précédente réellement validée et publiée pour
        # qu'elle puisse servir de cible de rollback.
        previous = _create_release(client, headers, version="edge-agent-0.2.9", sha="b" * 64)
        previous_id = previous["release_id"]
        assert _rollout(
            client, headers, previous_id, "canary", 0, canary_node_ids=[node["node_id"]]
        ).status_code == 200
        previous_offer = client.post(
            "/api/v1/center-edge/release/check",
            json=_machine(
                private_key,
                action="release.check",
                node_id=node["node_id"],
                center_id=center.id,
                sequence=2,
                fields={"current_version": "edge-agent-0.2.8"},
            ),
        )
        assert previous_offer.status_code == 200
        assert previous_offer.json()["release"]["release_id"] == previous_id
        previous_installed = _attest(
            client,
            private_key,
            node_id=node["node_id"],
            center_id=center.id,
            sequence=3,
            release_id=previous_id,
            version="edge-agent-0.2.9",
            result="installed",
            sha="b" * 64,
        )
        assert previous_installed.status_code == 200, previous_installed.text
        assert _rollout(client, headers, previous_id, "rolling", 100).status_code == 200
        assert _rollout(client, headers, previous_id, "released", 100).status_code == 200

        release = _create_release(
            client,
            headers,
            version="edge-agent-0.3.1",
            sha="a" * 64,
            rollback_release_id=previous_id,
        )
        release_id = release["release_id"]
        assert release["rollout_status"] == "draft"
        assert verify_release_manifest(release["manifest"], release["manifest_signature_b64"])
        tampered = dict(release["manifest"])
        tampered["software_version"] = "edge-agent-9.9.9"
        assert verify_release_manifest(tampered, release["manifest_signature_b64"]) is False

        # Draft invisible au gateway déjà sur la version précédente.
        no_draft_leak = client.post(
            "/api/v1/center-edge/release/check",
            json=_machine(
                private_key,
                action="release.check",
                node_id=node["node_id"],
                center_id=center.id,
                sequence=4,
                fields={"current_version": "edge-agent-0.2.9"},
            ),
        )
        assert no_draft_leak.status_code == 200, no_draft_leak.text
        assert no_draft_leak.json()["update_available"] is False

        canary = _rollout(
            client, headers, release_id, "canary", 0, canary_node_ids=[node["node_id"]]
        )
        assert canary.status_code == 200, canary.text
        offered = client.post(
            "/api/v1/center-edge/release/check",
            json=_machine(
                private_key,
                action="release.check",
                node_id=node["node_id"],
                center_id=center.id,
                sequence=5,
                fields={"current_version": "edge-agent-0.2.9"},
            ),
        )
        assert offered.status_code == 200, offered.text
        assert offered.json()["release"]["release_id"] == release_id

        staged = _attest(
            client,
            private_key,
            node_id=node["node_id"],
            center_id=center.id,
            sequence=6,
            release_id=release_id,
            version="edge-agent-0.3.1",
            result="staged",
            sha="a" * 64,
        )
        assert staged.status_code == 200, staged.text

        # Staged n'est pas suffisant : la promotion vers rolling reste bloquée.
        blocked = _rollout(client, headers, release_id, "rolling", 10)
        assert blocked.status_code == 409
        assert blocked.json()["detail"]["code"] == "EDGE_RELEASE_WAVE_NOT_VALIDATED"

        installed = _attest(
            client,
            private_key,
            node_id=node["node_id"],
            center_id=center.id,
            sequence=7,
            release_id=release_id,
            version="edge-agent-0.3.1",
            result="installed",
            sha="a" * 64,
        )
        assert installed.status_code == 200, installed.text
        rolling = _rollout(client, headers, release_id, "rolling", 10)
        assert rolling.status_code == 200, rolling.text

        # Une panne post-installation arrête automatiquement la diffusion.
        failed = _attest(
            client,
            private_key,
            node_id=node["node_id"],
            center_id=center.id,
            sequence=8,
            release_id=release_id,
            version="edge-agent-0.3.1",
            result="failed",
            sha="a" * 64,
        )
        assert failed.status_code == 200, failed.text
        releases = client.get("/api/v1/center-edge/releases", headers=headers).json()
        paused = next(item for item in releases if item["release_id"] == release_id)
        assert paused["rollout_status"] == "paused"

        # Une release dégradée ne peut plus être élargie, mais le rollback reste possible.
        promotion_after_failure = _rollout(client, headers, release_id, "rolling", 25)
        assert promotion_after_failure.status_code == 409
        rollback = _rollout(
            client,
            headers,
            release_id,
            "rollback",
            100,
            rollback_release_id=previous_id,
        )
        assert rollback.status_code == 200, rollback.text

        rollback_check = client.post(
            "/api/v1/center-edge/release/check",
            json=_machine(
                private_key,
                action="release.check",
                node_id=node["node_id"],
                center_id=center.id,
                sequence=9,
                fields={"current_version": "edge-agent-0.3.1"},
            ),
        )
        assert rollback_check.status_code == 200, rollback_check.text
        rollback_offer = rollback_check.json()
        assert rollback_offer["update_available"] is True
        assert rollback_offer["action"] == "rollback"
        assert rollback_offer["source_release_id"] == release_id
        assert rollback_offer["release"]["release_id"] == previous_id


def test_release_rejects_private_artifact_url() -> None:
    init_db()
    with TestClient(app) as client:
        headers = _super_admin_headers(client)
        response = client.post(
            "/api/v1/center-edge/releases",
            headers=headers,
            json={
                "software_version": "edge-agent-0.3.1",
                "artifact_url": "https://127.0.0.1/private-release.tar.gz",
                "artifact_sha256": "c" * 64,
                "artifact_size_bytes": 4096,
            },
        )
        assert response.status_code == 422
