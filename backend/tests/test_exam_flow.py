from datetime import datetime, timedelta
from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app


def test_exam_attempt_can_be_started_and_submitted() -> None:
    with TestClient(app) as client:
        suffix = str(uuid4())[:8]
        center = client.post("/api/v1/centers", json={"code": f"CTR-{suffix}", "name": "Centre test", "city": "Conakry", "address": "Dixinn", "capacity": 20, "status": "active"}).json()
        candidate = client.post("/api/v1/candidates", json={"first_name": "Aissatou", "last_name": "Bah", "identity_number": f"GN-{suffix}", "phone": "+224111111111", "permit_category": "B"}).json()
        session = client.post("/api/v1/sessions", json={"center_id": center["id"], "starts_at": (datetime.utcnow() + timedelta(days=1)).isoformat(), "capacity": 20}).json()
        question = client.post("/api/v1/questions", json={"category": "signalisation", "text": "Feu rouge ?", "options": ["Stop", "Passer"], "correct_answer": "Stop"}).json()

        attempt_response = client.post("/api/v1/exams/start", json={"candidate_id": candidate["id"], "session_id": session["id"]})
        assert attempt_response.status_code == 201
        attempt = attempt_response.json()

        submit_response = client.post(f"/api/v1/exams/{attempt['id']}/submit", json={"answers": {question["id"]: "Stop"}})
        assert submit_response.status_code == 200
        assert submit_response.json()["status"] == "submitted"
