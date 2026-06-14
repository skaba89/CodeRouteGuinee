from fastapi.testclient import TestClient

from app.main import app


def test_exam_certificate_verification_returns_invalid_for_unknown_attempt() -> None:
    with TestClient(app) as client:
        response = client.get("/api/v1/exams/unknown-attempt/certificate/verify")

    assert response.status_code == 200
    data = response.json()
    assert data["valid"] is False
    assert data["attempt_id"] == "unknown-attempt"
    assert data["status"] == "not_found"
