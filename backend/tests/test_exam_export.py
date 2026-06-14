from fastapi.testclient import TestClient

from app.main import app


def test_exam_attempts_export_csv_requires_admin_auth() -> None:
    with TestClient(app) as client:
        response = client.get("/api/v1/exams/export.csv")

    assert response.status_code == 401
