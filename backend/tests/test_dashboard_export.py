from fastapi.testclient import TestClient

from app.main import app


def test_dashboard_export_csv_returns_expected_headers() -> None:
    with TestClient(app) as client:
        response = client.get("/api/v1/dashboard/export.csv")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    body = response.text
    assert "metric,value" in body
    assert "candidates" in body
    assert "accredited_centers" in body
    assert "exam_sessions" in body
