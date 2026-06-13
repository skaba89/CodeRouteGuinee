from datetime import datetime, timedelta

from fastapi.testclient import TestClient

from app.main import app


def test_candidate_center_question_and_dashboard_routes() -> None:
    client = TestClient(app)

    center_payload = {
        "code": "CTR-KALOUM-TEST",
        "name": "Centre agree Kaloum Test",
        "city": "Conakry",
        "address": "Kaloum",
        "capacity": 20,
        "status": "active",
    }
    center_response = client.post("/api/v1/centers", json=center_payload)
    assert center_response.status_code in (201, 409)

    candidate_response = client.post(
        "/api/v1/candidates",
        json={
            "first_name": "Mamadou",
            "last_name": "Diallo",
            "identity_number": "GN-TEST-001",
            "phone": "+224000000000",
            "permit_category": "B",
        },
    )
    assert candidate_response.status_code == 201
    assert candidate_response.json()["reference"].startswith("GN-CODE-")

    question_response = client.post(
        "/api/v1/questions",
        json={
            "category": "priorite",
            "text": "Que faire a un panneau STOP ?",
            "options": ["S'arreter", "Accelerer", "Klaxonner"],
            "correct_answer": "S'arreter",
        },
    )
    assert question_response.status_code == 201

    centers = client.get("/api/v1/centers").json()
    assert isinstance(centers, list)
    center_id = centers[0]["id"]

    session_response = client.post(
        "/api/v1/sessions",
        json={
            "center_id": center_id,
            "starts_at": (datetime.utcnow() + timedelta(days=1)).isoformat(),
            "capacity": 20,
        },
    )
    assert session_response.status_code == 201
    assert session_response.json()["reference"].startswith("GN-SESSION-")

    dashboard_response = client.get("/api/v1/dashboard")
    assert dashboard_response.status_code == 200
    assert dashboard_response.json()["candidates"] >= 1
