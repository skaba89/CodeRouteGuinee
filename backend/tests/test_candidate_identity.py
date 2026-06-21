from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db.session import SessionLocal
from app.main import app
from app.models_audit import AuditLog
from app.routers import auth as _auth_module
from tests.conftest import TEST_BOOTSTRAP_TOKEN


def _admin_headers(client: TestClient) -> dict[str, str]:
    suffix = str(uuid4())[:8]
    email = f"admin-identity-{suffix}@coderoute.gn"
    password = "StrongPass123!"
    _auth_module.settings.admin_registration_token = TEST_BOOTSTRAP_TOKEN
    response = client.post(
        "/api/v1/auth/register",
        headers={"X-Admin-Registration-Token": TEST_BOOTSTRAP_TOKEN},
            json={"email": email, "full_name": "Admin Identite", "password": password, "role": "admin"},
    )
    assert response.status_code == 201
    token_response = client.post("/api/v1/auth/login", data={"username": email, "password": password})
    assert token_response.status_code == 200
    return {"Authorization": f"Bearer {token_response.json()['access_token']}"}


def _candidate(client: TestClient, headers: dict) -> dict:
    suffix = str(uuid4())[:8]
    response = client.post(
        "/api/v1/candidates",
        headers=headers,
        json={
            "first_name": "Mariam",
            "last_name": "Diallo",
            "identity_number": f"NINA-{suffix}",
            "phone": "+224620000000",
            "permit_category": "B",
        },
    )
    assert response.status_code == 201
    return response.json()


def test_candidate_identity_submission_creates_pending_check() -> None:
    with TestClient(app) as client:
        headers = _admin_headers(client)
        candidate = _candidate(client, headers)
        response = client.post(
            "/api/v1/candidate-identity",
            headers=headers,
            json={
                "candidate_id": candidate["id"],
                "document_type": "national_id",
                "document_reference": "NINA-2026-0001",
                "photo_reference": "photos/mariam-diallo.jpg",
            },
        )

    assert response.status_code == 201
    payload = response.json()
    assert payload["candidate_id"] == candidate["id"]
    assert payload["status"] == "pending"


def test_candidate_identity_list_requires_admin_authentication() -> None:
    with TestClient(app) as client:
        response = client.get("/api/v1/candidate-identity")

    assert response.status_code == 401


def test_admin_can_decide_candidate_identity_with_audit_log() -> None:
    with TestClient(app) as client:
        headers = _admin_headers(client)
        candidate = _candidate(client, headers)
        created = client.post(
            "/api/v1/candidate-identity",
            headers=headers,
            json={
                "candidate_id": candidate["id"],
                "document_type": "passport",
                "document_reference": "P-GN-2026-77",
            },
        ).json()

        listed = client.get("/api/v1/candidate-identity", headers=headers)
        assert listed.status_code == 200
        assert any(item["id"] == created["id"] for item in listed.json())

        decision = client.post(
            f"/api/v1/candidate-identity/{created['id']}/decision",
            headers=headers,
            json={"status": "verified", "reason": "Document conforme au registre presente"},
        )

        assert decision.status_code == 200
        assert decision.json()["status"] == "verified"
        assert decision.json()["decision_reason"] == "Document conforme au registre presente"

        with SessionLocal() as db:
            audit_log = db.scalar(
                select(AuditLog)
                .where(AuditLog.entity == "candidate_identity")
                .where(AuditLog.entity_id == created["id"])
                .where(AuditLog.action == "candidate_identity.verified")
            )
            assert audit_log is not None
            assert audit_log.details["candidate_id"] == candidate["id"]
