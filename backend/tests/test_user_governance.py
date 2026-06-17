from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db.session import SessionLocal
from app.main import app
from app.models_audit import AuditLog


def register_user(client: TestClient, role: str) -> dict:
    suffix = str(uuid4())[:8]
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": f"{role}-{suffix}@coderoute.gn",
            "full_name": f"{role} CodeRoute",
            "password": "StrongPass123",
            "role": role,
        },
    )
    assert response.status_code == 201
    return response.json()


def login_token(client: TestClient, email: str) -> str:
    response = client.post("/api/v1/auth/login", data={"username": email, "password": "StrongPass123"})
    assert response.status_code == 200
    return response.json()["access_token"]


def test_admin_can_list_users() -> None:
    with TestClient(app) as client:
        admin = register_user(client, "admin")
        register_user(client, "candidate")
        token = login_token(client, admin["email"])

        response = client.get("/api/v1/users", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    assert any(user["email"] == admin["email"] for user in response.json())


def test_super_admin_can_create_institutional_user_with_audit_log() -> None:
    with TestClient(app) as client:
        super_admin = register_user(client, "super_admin")
        token = login_token(client, super_admin["email"])
        email = f"agent-{str(uuid4())[:8]}@coderoute.gn"

        response = client.post(
            "/api/v1/users",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "email": email,
                "full_name": "Agent Centre Agree",
                "initial_password": "TemporaryPass123",
                "role": "center",
                "reason": "Creation officielle du compte centre",
            },
        )

    assert response.status_code == 201
    created_user = response.json()
    assert created_user["email"] == email
    assert created_user["role"] == "center"
    assert created_user["is_active"] is True

    db = SessionLocal()
    try:
        action = db.scalar(
            select(AuditLog.action).where(AuditLog.entity == "user", AuditLog.entity_id == created_user["id"])
        )
    finally:
        db.close()

    assert action == "user.created"


def test_admin_cannot_create_institutional_user() -> None:
    with TestClient(app) as client:
        admin = register_user(client, "admin")
        token = login_token(client, admin["email"])

        response = client.post(
            "/api/v1/users",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "email": f"agent-{str(uuid4())[:8]}@coderoute.gn",
                "full_name": "Agent Centre Agree",
                "initial_password": "TemporaryPass123",
                "role": "center",
                "reason": "Creation officielle du compte centre",
            },
        )

    assert response.status_code == 403


def test_super_admin_can_update_role_and_status_with_audit_log() -> None:
    with TestClient(app) as client:
        super_admin = register_user(client, "super_admin")
        candidate = register_user(client, "candidate")
        token = login_token(client, super_admin["email"])

        role_response = client.patch(
            f"/api/v1/users/{candidate['id']}/role",
            headers={"Authorization": f"Bearer {token}"},
            json={"role": "center", "reason": "Affectation officielle au centre agree"},
        )
        status_response = client.patch(
            f"/api/v1/users/{candidate['id']}/status",
            headers={"Authorization": f"Bearer {token}"},
            json={"is_active": False, "reason": "Suspension administrative temporaire"},
        )

    assert role_response.status_code == 200
    assert role_response.json()["role"] == "center"
    assert status_response.status_code == 200
    assert status_response.json()["is_active"] is False

    db = SessionLocal()
    try:
        actions = db.scalars(
            select(AuditLog.action).where(AuditLog.entity == "user", AuditLog.entity_id == candidate["id"])
        ).all()
    finally:
        db.close()

    assert "user.role_updated" in actions
    assert "user.status_updated" in actions


def test_admin_cannot_update_user_role() -> None:
    with TestClient(app) as client:
        admin = register_user(client, "admin")
        candidate = register_user(client, "candidate")
        token = login_token(client, admin["email"])

        response = client.patch(
            f"/api/v1/users/{candidate['id']}/role",
            headers={"Authorization": f"Bearer {token}"},
            json={"role": "center", "reason": "Affectation officielle au centre agree"},
        )

    assert response.status_code == 403


def test_super_admin_cannot_deactivate_or_demote_self() -> None:
    with TestClient(app) as client:
        super_admin = register_user(client, "super_admin")
        token = login_token(client, super_admin["email"])

        status_response = client.patch(
            f"/api/v1/users/{super_admin['id']}/status",
            headers={"Authorization": f"Bearer {token}"},
            json={"is_active": False, "reason": "Erreur de manipulation"},
        )
        role_response = client.patch(
            f"/api/v1/users/{super_admin['id']}/role",
            headers={"Authorization": f"Bearer {token}"},
            json={"role": "admin", "reason": "Erreur de manipulation"},
        )

    assert status_response.status_code == 400
    assert role_response.status_code == 400
