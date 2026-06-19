from fastapi.testclient import TestClient

from app.main import app
from tests.conftest import get_admin_headers


def test_exam_summary_endpoint_returns_expected_shape() -> None:
    with TestClient(app) as client:
        headers = get_admin_headers(client)
        response = client.get("/api/v1/exams/summary", headers=headers)

    assert response.status_code == 200
    data = response.json()
    assert "total_attempts" in data
    assert "submitted_attempts" in data
    assert "passed_attempts" in data
    assert "failed_attempts" in data
    assert "average_score" in data
