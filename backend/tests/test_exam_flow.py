from datetime import datetime, timedelta
from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app


def _admin_headers(client: TestClient) -> dict[str, str]:
    suffix = str(uuid4())[:8]
    email = f"admin-exam-{suffix}@coderoute.gn"
    password = "StrongPass123"
    response = client.post(
        "/api/v1/auth/register",
        json={"email": email, "full_name": "Admin Exam", "password": password, "role": "admin"},
    )
    assert response.status_code == 201
    token_response = client.post("/api/v1/auth/login", data={"username": email, "password": password})
    assert token_response.status_code == 200
    return {"Authorization": f"Bearer {token_response.json()['access_token']}"}


def test_exam_attempt_can_be_started_and_submitted() -> None:
    with TestClient(app) as client:
        suffix = str(uuid4())[:8]
        headers = _admin_headers(client)
        center = client.post("/api/v1/centers", headers=headers, json={"code": f"CTR-{suffix}", "name": "Centre test", "city": "Conakry", "address": "Dixinn", "capacity": 20, "status": "active"}).json()
        candidate = client.post("/api/v1/candidates", json={"first_name": "Aissatou", "last_name": "Bah", "identity_number": f"GN-{suffix}", "phone": "+224111111111", "permit_category": "B"}).json()
        session = client.post("/api/v1/sessions", headers=headers, json={"center_id": center["id"], "starts_at": (datetime.utcnow() + timedelta(days=1)).isoformat(), "capacity": 20}).json()
        question = client.post("/api/v1/questions", headers=headers, json={"category": "signalisation", "text": "Feu rouge ?", "options": ["Stop", "Passer"], "correct_answer": "Stop"}).json()

        attempt_response = client.post("/api/v1/exams/start", json={"candidate_id": candidate["id"], "session_id": session["id"]})
        assert attempt_response.status_code == 201
        attempt = attempt_response.json()

        submit_response = client.post(f"/api/v1/exams/{attempt['id']}/submit", json={"answers": {question["id"]: "Stop"}})
        assert submit_response.status_code == 200
        assert submit_response.json()["status"] == "submitted"
