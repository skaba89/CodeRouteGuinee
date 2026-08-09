from __future__ import annotations

import base64
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
)
from app.main import app
from app.models_center import Center


def _b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _admin_headers(client: TestClient) -> dict[str, str]:
    suffix = uuid4().hex
    email = f"fleet-admin-{suffix}@coderoute.local"
    password = "FleetAdminPass123!"
    register = client.post(
        "/api/v1/auth/register",
        json={"email": email, "full_name": "Admin Fleet Test", "password": password, "role": "admin"},
    )
    assert register.status_code == 201
    login = client.post("/api/v1/auth/login", data={"username": email, "password": password})
    assert login.status_code == 200
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def _create_center() -> Center:
    suffix = uuid4().hex[:10].upper()
    center = Center(
        code=f"FLEET-{suffix}",
        name="Centre Fleet P7",
        city="Conakry",
        address="Centre national de supervision",
        capacity=40,
        status="accredited",
    )
    with SessionLocal() as db:
        db.add(center)
        db.commit()
        db.refresh(center)
        db.expunge(center)
    return center


def _heartbeat(
    private_key: Ed25519PrivateKey,
    *,
    node_id: str,
    center_id: str,
    sequence: int,
    telemetry: dict | None,
    version: str = EDGE_TARGET_SOFTWARE_VERSION,
) -> dict:
    sent_at = datetime.now(UTC).replace(microsecond=0)
    capabilities = list(EDGE_REQUIRED_CAPABILITIES)
    signing = heartbeat_signing_payload(
        node_id=node_id,
        center_id=center_id,
        sequence=sequence,
        sent_at=sent_at,
        software_version=version,
        capabilities=capabilities,
        telemetry=telemetry,
    )
    signature = private_key.sign(canonical_edge_payload(signing))
    return {**signing, "signature_b64": _b64url(signature)}


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
            "label": "Gateway Fleet Salle A",
            "public_key_b64": _b64url(public_raw),
            "capabilities": list(EDGE_REQUIRED_CAPABILITIES),
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_fleet_aggregates_signed_operational_telemetry() -> None:
    init_db()
    private_key = Ed25519PrivateKey.generate()

    with TestClient(app) as client:
        headers = _admin_headers(client)
        center = _create_center()
        node = _enroll(client, headers, center, private_key)
        telemetry = {
            "active_leases": 2,
            "finalized_leases": 8,
            "synced_leases": 120,
            "sync_pending": 8,
            "revalidation_required": 0,
            "corrupt_leases": 0,
            "media_files": 42,
            "media_bytes": 12_500_000,
        }
        heartbeat = _heartbeat(
            private_key,
            node_id=node["node_id"],
            center_id=center.id,
            sequence=1,
            telemetry=telemetry,
        )
        accepted = client.post("/api/v1/center-edge/heartbeat", json=heartbeat)
        assert accepted.status_code == 200, accepted.text
        assert accepted.json()["target_software_version"] == EDGE_TARGET_SOFTWARE_VERSION

        fleet = client.get("/api/v1/center-edge/fleet", headers=headers)
        assert fleet.status_code == 200, fleet.text
        body = fleet.json()
        assert body["target_software_version"] == EDGE_TARGET_SOFTWARE_VERSION
        assert body["summary"]["sync_pending"] >= 8
        target_node = next(item for item in body["nodes"] if item["node_id"] == node["node_id"])
        assert target_node["online"] is True
        assert target_node["telemetry"]["sync_pending"] == 8
        assert target_node["version_drift"] is False
        assert target_node["missing_capabilities"] == []
        assert target_node["health_status"] in {"healthy", "degraded"}
        assert "public_key_b64" not in target_node
        assert "last_observed_ip" not in target_node

        target_center = next(item for item in body["centers"] if item["center_id"] == center.id)
        assert target_center["node_count"] == 1
        assert target_center["online_nodes"] == 1
        assert target_center["sync_pending"] == 8
        assert body["rollout"]["compliant_nodes"] >= 1


def test_fleet_telemetry_is_covered_by_ed25519_signature() -> None:
    init_db()
    private_key = Ed25519PrivateKey.generate()

    with TestClient(app) as client:
        headers = _admin_headers(client)
        center = _create_center()
        node = _enroll(client, headers, center, private_key)
        heartbeat = _heartbeat(
            private_key,
            node_id=node["node_id"],
            center_id=center.id,
            sequence=1,
            telemetry={
                "active_leases": 1,
                "finalized_leases": 1,
                "synced_leases": 4,
                "sync_pending": 1,
                "revalidation_required": 0,
                "corrupt_leases": 0,
                "media_files": 10,
                "media_bytes": 500_000,
            },
        )
        heartbeat["telemetry"]["sync_pending"] = 99
        rejected = client.post("/api/v1/center-edge/heartbeat", json=heartbeat)
        assert rejected.status_code == 401


def test_legacy_heartbeat_remains_accepted_but_is_flagged_for_upgrade() -> None:
    init_db()
    private_key = Ed25519PrivateKey.generate()

    with TestClient(app) as client:
        headers = _admin_headers(client)
        center = _create_center()
        node = _enroll(client, headers, center, private_key)
        heartbeat = _heartbeat(
            private_key,
            node_id=node["node_id"],
            center_id=center.id,
            sequence=1,
            telemetry=None,
            version="edge-agent-0.1.0",
        )
        # Simuler réellement un agent ancien : retirer les capacités P7 puis re-signer.
        heartbeat["capabilities"] = ["answer-journal-v1", "exam-lease-v1", "media-prefetch-v1"]
        signing = heartbeat_signing_payload(
            node_id=node["node_id"],
            center_id=center.id,
            sequence=1,
            sent_at=datetime.fromisoformat(heartbeat["sent_at"].replace("Z", "+00:00")),
            software_version="edge-agent-0.1.0",
            capabilities=heartbeat["capabilities"],
            telemetry=None,
        )
        heartbeat["signature_b64"] = _b64url(private_key.sign(canonical_edge_payload(signing)))

        accepted = client.post("/api/v1/center-edge/heartbeat", json=heartbeat)
        assert accepted.status_code == 200, accepted.text
        fleet = client.get("/api/v1/center-edge/fleet", headers=headers).json()
        target_node = next(item for item in fleet["nodes"] if item["node_id"] == node["node_id"])
        assert target_node["version_drift"] is True
        assert "fleet-telemetry-v1" in target_node["missing_capabilities"]
        assert any(alert["code"] == "EDGE_TELEMETRY_MISSING" for alert in target_node["alerts"])
        assert fleet["rollout"]["upgrade_required_nodes"] >= 1
