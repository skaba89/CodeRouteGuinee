from fastapi.testclient import TestClient

from app.main import app


def test_exam_attempts_export_csv_has_expected_headers() -> None:
    with TestClient(app) as client:
        response = client.get("/api/v1/exams/export.csv")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert "attempt_id;candidate_reference;candidate_name" in response.text
