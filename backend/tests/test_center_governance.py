from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db.session import SessionLocal
from app.main import app
from app.models_audit import AuditLog


def _admin_headers(client: TestClient) -> dict[str, str]:
    suffix = str(uuid4())[:8]
    email = f"admin-center-{suffix}@coderoute.gn"
    password = "StrongPass123"
    response = client.post(
        "/api/v1/auth/register",
        json={"email": email, "full_name": "Admin Centre", "password": password, "role": "admin"},
    )
    assert response.status_code == 201
    token_response = client.post("/api/v1/auth/login", data={"username": email, "password": password})
    assert token_response.status_code == 200
    return {"Authorization": f"Bearer {token_response.json()['access_token']}"}


def test_center_status_update_requires_admin_authentication() -> None:
    with TestClient(app) as client:
        response = client.patch(
            "/api/v1/centers/unknown/status",
            json={"status": "suspended", "reason": "Controle administratif"},
        )

    assert response.status_code == 401


def test_admin_can_accredit_and_suspend_center_with_audit_log() -> None:
    with TestClient(app) as client:
        suffix = str(uuid4())[:8]
        headers = _admin_headers(client)
        center_response = client.post(
            "/api/v1/centers",
            headers=headers,
            json={
                "code": f"GOV-{suffix}",
                "name": "Centre Gouvernance",
                "city": "Conakry",
                "address": "Kaloum",
                "capacity": 25,
                "status": "pending_audit",
            },
        )
        assert center_response.status_code == 201
        center = center_response.json()

        accredited_response = client.patch(
            f"/api/v1/centers/{center['id']}/status",
            headers=headers,
            json={"status": "accredited", "reason": "Audit institutionnel valide"},
        )
        assert accredited_response.status_code == 200
        assert accredited_response.json()["status"] == "accredited"

        suspended_response = client.patch(
            f"/api/v1/centers/{center['id']}/status",
            headers=headers,
            json={"status": "suspended", "reason": "Suspension administrative"},
        )
        assert suspended_response.status_code == 200
        assert suspended_response.json()["status"] == "suspended"

        with SessionLocal() as db:
            logs = db.scalars(
                select(AuditLog)
                .where(AuditLog.entity == "center")
                .where(AuditLog.entity_id == center["id"])
                .where(AuditLog.action == "center.status_updated")
            ).all()
            assert len(logs) >= 2
            assert any(log.details["new_status"] == "suspended" for log in logs)
