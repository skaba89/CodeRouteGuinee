from __future__ import annotations

import base64
from datetime import UTC, datetime
from uuid import uuid4

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from fastapi.testclient import TestClient

from app.db.session import SessionLocal, init_db
from app.edge_gateway import canonical_edge_payload, heartbeat_signing_payload, iso_z
from app.main import app
from app.models_center import Center


def _b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _admin_headers(client: TestClient) -> dict[str, str]:
    suffix = uuid4().hex
    email = f"edge-admin-{suffix}@coderoute.local"
    password = "EdgeAdminPass123!"
    register = client.post(
        "/api/v1/auth/register",
        json={"email": email, "full_name": "Admin Edge Test", "password": password, "role": "admin"},
    )
    assert register.status_code == 201
    login = client.post(
        "/api/v1/auth/login",
        data={"username": email, "password": password},
    )
    assert login.status_code == 200
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def _create_center() -> Center:
    suffix = uuid4().hex[:10].upper()
    center = Center(
        code=f"EDGE-{suffix}",
        name="Centre pilote Edge",
        city="Conakry",
        address="Centre technique pilote",
        capacity=35,
        status="accredited",
    )
    with SessionLocal() as db:
        db.add(center)
        db.commit()
        db.refresh(center)
        db.expunge(center)
    return center


def _signed_heartbeat(
    private_key: Ed25519PrivateKey,
    *,
    node_id: str,
    center_id: str,
    sequence: int,
    sent_at: datetime,
    software_version: str = "edge-0.1.0",
) -> dict:
    capabilities = ["exam-lease-v1", "answer-journal-v1"]
    signing_payload = heartbeat_signing_payload(
        node_id=node_id,
        center_id=center_id,
        sequence=sequence,
        sent_at=sent_at,
        software_version=software_version,
        capabilities=capabilities,
    )
    signature = private_key.sign(canonical_edge_payload(signing_payload))
    return {
        **signing_payload,
        "signature_b64": _b64url(signature),
    }


def test_center_edge_enrollment_signed_heartbeat_replay_and_revocation() -> None:
    init_db()
    private_key = Ed25519PrivateKey.generate()
    public_raw = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    public_b64 = _b64url(public_raw)

    with TestClient(app) as client:
        headers = _admin_headers(client)
        center = _create_center()

        enroll = client.post(
            "/api/v1/center-edge/nodes",
            headers=headers,
            json={
                "center_id": center.id,
                "label": "Gateway Edge Salle A",
                "public_key_b64": public_b64,
                "capabilities": ["answer-journal-v1", "exam-lease-v1"],
            },
        )
        assert enroll.status_code == 201, enroll.text
        node = enroll.json()
        assert node["center_id"] == center.id
        assert node["status"] == "active"
        assert node["online"] is False
        assert len(node["public_key_fingerprint"]) == 64

        now = datetime.now(UTC).replace(microsecond=0)
        heartbeat_1 = _signed_heartbeat(
            private_key,
            node_id=node["node_id"],
            center_id=center.id,
            sequence=1,
            sent_at=now,
        )
        accepted = client.post("/api/v1/center-edge/heartbeat", json=heartbeat_1)
        assert accepted.status_code == 200, accepted.text
        assert accepted.json()["accepted"] is True
        assert accepted.json()["sequence"] == 1

        replay = client.post("/api/v1/center-edge/heartbeat", json=heartbeat_1)
        assert replay.status_code == 409
        assert replay.json()["detail"]["code"] == "EDGE_HEARTBEAT_REPLAY"

        heartbeat_2 = _signed_heartbeat(
            private_key,
            node_id=node["node_id"],
            center_id=center.id,
            sequence=2,
            sent_at=now,
        )
        heartbeat_2["signature_b64"] = _b64url(b"0" * 64)
        invalid_signature = client.post("/api/v1/center-edge/heartbeat", json=heartbeat_2)
        assert invalid_signature.status_code == 401

        heartbeat_2 = _signed_heartbeat(
            private_key,
            node_id=node["node_id"],
            center_id=center.id,
            sequence=2,
            sent_at=datetime.now(UTC).replace(microsecond=0),
        )
        accepted_2 = client.post("/api/v1/center-edge/heartbeat", json=heartbeat_2)
        assert accepted_2.status_code == 200, accepted_2.text

        readiness = client.get("/api/v1/center-edge/readiness", headers=headers, params={"center_id": center.id})
        assert readiness.status_code == 200
        readiness_body = readiness.json()
        assert readiness_body["status"] == "ready"
        assert readiness_body["active_nodes"] == 1
        assert readiness_body["online_nodes"] == 1
        assert readiness_body["stale_nodes"] == 0

        revoke = client.post(
            f"/api/v1/center-edge/nodes/{node['node_id']}/status",
            headers=headers,
            json={"status": "revoked", "reason": "Simulation de compromission de la clé privée"},
        )
        assert revoke.status_code == 200
        assert revoke.json()["status"] == "revoked"

        heartbeat_3 = _signed_heartbeat(
            private_key,
            node_id=node["node_id"],
            center_id=center.id,
            sequence=3,
            sent_at=datetime.now(UTC).replace(microsecond=0),
        )
        blocked = client.post("/api/v1/center-edge/heartbeat", json=heartbeat_3)
        assert blocked.status_code == 403

        reactivate = client.post(
            f"/api/v1/center-edge/nodes/{node['node_id']}/status",
            headers=headers,
            json={"status": "active", "reason": "Tentative de réactivation interdite"},
        )
        assert reactivate.status_code == 409
        assert reactivate.json()["detail"]["code"] == "EDGE_REVOCATION_IS_FINAL"


def test_center_edge_rejects_clock_skew() -> None:
    init_db()
    private_key = Ed25519PrivateKey.generate()
    public_raw = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )

    with TestClient(app) as client:
        headers = _admin_headers(client)
        center = _create_center()
        enroll = client.post(
            "/api/v1/center-edge/nodes",
            headers=headers,
            json={
                "center_id": center.id,
                "label": "Gateway Edge Horloge",
                "public_key_b64": _b64url(public_raw),
                "capabilities": ["exam-lease-v1"],
            },
        )
        assert enroll.status_code == 201
        node_id = enroll.json()["node_id"]

        old = datetime(2020, 1, 1, tzinfo=UTC)
        heartbeat = _signed_heartbeat(
            private_key,
            node_id=node_id,
            center_id=center.id,
            sequence=1,
            sent_at=old,
        )
        response = client.post("/api/v1/center-edge/heartbeat", json=heartbeat)
        assert response.status_code == 409
        assert response.json()["detail"]["code"] == "EDGE_CLOCK_SKEW_TOO_HIGH"

        server_time = client.get("/api/v1/center-edge/time")
        assert server_time.status_code == 200
        assert server_time.json()["heartbeat_interval_seconds"] == 60
        assert server_time.json()["max_clock_skew_seconds"] == 300
        assert iso_z(datetime.now(UTC)).endswith("Z")
