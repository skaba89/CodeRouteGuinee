from datetime import datetime, timedelta, UTC
from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app


def _admin_headers(client: TestClient) -> dict[str, str]:
    suffix = str(uuid4())[:8]
    email = f"admin-api-{suffix}@coderoute.gn"
    password = "StrongPass123"
    response = client.post(
        "/api/v1/auth/register",
        json={"email": email, "full_name": "Admin API", "password": password, "role": "admin"},
    )
    assert response.status_code == 201
    token_response = client.post("/api/v1/auth/login", data={"username": email, "password": password})
    assert token_response.status_code == 200
    return {"Authorization": f"Bearer {token_response.json()['access_token']}"}


def test_candidate_center_question_and_dashboard_routes() -> None:
    with TestClient(app) as client:
        suffix = str(uuid4())[:8]
        headers = _admin_headers(client)
        center_payload = {
            "code": f"CTR-KALOUM-{suffix}",
            "name": "Centre agree Kaloum Test",
            "city": "Conakry",
            "address": "Kaloum",
            "capacity": 20,
            "status": "active",
        }
        center_response = client.post("/api/v1/centers", headers=headers, json=center_payload)
        assert center_response.status_code == 201

        candidate_response = client.post(
            "/api/v1/candidates",
            headers=headers,
            json={
                "first_name": "Mamadou",
                "last_name": "Diallo",
                "identity_number": f"GN-TEST-{suffix}",
                "phone": "+224000000000",
                "permit_category": "B",
            },
        )
        assert candidate_response.status_code == 201
        assert candidate_response.json()["reference"].startswith("GN-CODE-")

        question_response = client.post(
            "/api/v1/questions",
            headers=headers,
            json={
                "category": "priorite",
                "text": "Que faire a un panneau STOP ?",
                "options": ["S'arreter", "Accelerer", "Klaxonner"],
                "correct_answer": "S'arreter",
            },
        )
        assert question_response.status_code == 201

        centers = client.get("/api/v1/centers", headers=headers).json()
        assert isinstance(centers, list)
        center_id = centers[0]["id"]

        session_response = client.post(
            "/api/v1/sessions",
            headers=headers,
            json={
                "center_id": center_id,
                "starts_at": (datetime.now(UTC) + timedelta(days=1)).isoformat(),
                "capacity": 20,
            },
        )
        assert session_response.status_code == 201
        assert session_response.json()["reference"].startswith("GN-SESSION-")

        dashboard_response = client.get("/api/v1/dashboard", headers=headers)
        assert dashboard_response.status_code == 200
        assert dashboard_response.json()["candidates"] >= 1
