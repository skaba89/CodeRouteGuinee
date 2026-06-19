from datetime import datetime, timedelta
from app.time_utils import utc_now
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db.session import SessionLocal
from app.main import app
from app.models_audit import AuditLog


def _admin_headers(client: TestClient) -> dict[str, str]:
    suffix = str(uuid4())[:8]
    email = f"admin-authz-{suffix}@coderoute.gn"
    password = "StrongPass123"
    response = client.post(
        "/api/v1/auth/register",
        json={"email": email, "full_name": "Admin Habilitations", "password": password, "role": "admin"},
    )
    assert response.status_code == 201
    token_response = client.post("/api/v1/auth/login", data={"username": email, "password": password})
    assert token_response.status_code == 200
    return {"Authorization": f"Bearer {token_response.json()['access_token']}"}


def test_institutional_authorizations_require_admin_authentication() -> None:
    with TestClient(app) as client:
        response = client.get("/api/v1/institutional-authorizations")

    assert response.status_code == 401


def test_admin_can_create_and_approve_institutional_authorization_with_audit_log() -> None:
    with TestClient(app) as client:
        suffix = str(uuid4())[:8]
        headers = _admin_headers(client)
        create_response = client.post(
            "/api/v1/institutional-authorizations",
            headers=headers,
            json={
                "authority": "Ministere des Transports",
                "reference": f"MT-CODE-{suffix}",
                "title": "Convention pilote CodeRoute Guinee",
                "scope": "Autorisation pilote pour la digitalisation des examens du code de la route.",
                "valid_from": utc_now().isoformat(),
                "valid_until": (utc_now() + timedelta(days=365)).isoformat(),
            },
        )
        assert create_response.status_code == 201
        authorization = create_response.json()
        assert authorization["status"] == "draft"

        approve_response = client.patch(
            f"/api/v1/institutional-authorizations/{authorization['id']}/status",
            headers=headers,
            json={"status": "approved", "reason": "Convention signee et validee pour pilote"},
        )
        assert approve_response.status_code == 200
        assert approve_response.json()["status"] == "approved"

        listed = client.get("/api/v1/institutional-authorizations?status_filter=approved", headers=headers)
        assert listed.status_code == 200
        assert any(item["id"] == authorization["id"] for item in listed.json())

        with SessionLocal() as db:
            audit_log = db.scalar(
                select(AuditLog)
                .where(AuditLog.entity == "institutional_authorization")
                .where(AuditLog.entity_id == authorization["id"])
                .where(AuditLog.action == "institutional_authorization.status_updated")
            )
            assert audit_log is not None
            assert audit_log.details["new_status"] == "approved"
