from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app


def test_register_login_and_me() -> None:
    with TestClient(app) as client:
        suffix = str(uuid4())[:8]
        email = f"admin-{suffix}@coderoute.gn"
        password = "StrongPass123"

        register_response = client.post(
            "/api/v1/auth/register",
            json={
                "email": email,
                "full_name": "Admin CodeRoute",
                "password": password,
                "role": "admin",
            },
        )
        assert register_response.status_code == 201
        assert register_response.json()["role"] == "admin"

        login_response = client.post(
            "/api/v1/auth/login",
            data={"username": email, "password": password},
        )
        assert login_response.status_code == 200
        token = login_response.json()["access_token"]

        me_response = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert me_response.status_code == 200
        assert me_response.json()["email"] == email
