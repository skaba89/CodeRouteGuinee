from types import SimpleNamespace

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db.session import SessionLocal
from app.deps import get_current_user
from app.main import app
from app.models_audit import AuditLog


def test_dashboard_export_csv_requires_authentication() -> None:
    with TestClient(app) as client:
        response = client.get("/api/v1/dashboard/export.csv")

    assert response.status_code == 401


def test_institutional_readiness_requires_authentication() -> None:
    with TestClient(app) as client:
        response = client.get("/api/v1/dashboard/institutional-readiness")

    assert response.status_code == 401


def test_institutional_readiness_returns_executive_summary_for_admin() -> None:
    admin_user = SimpleNamespace(id="test-readiness-admin", role="admin", is_active=True)
    app.dependency_overrides[get_current_user] = lambda: admin_user

    try:
        with TestClient(app) as client:
            response = client.get("/api/v1/dashboard/institutional-readiness")

        assert response.status_code == 200
        payload = response.json()
        assert 0 <= payload["score"] <= 100
        assert payload["label"]
        assert payload["summary"]
        assert len(payload["items"]) == 5
        assert {item["pillar"] for item in payload["items"]} >= {"Gouvernance nationale", "Tracabilite et audit"}

        with SessionLocal() as db:
            audit_log = db.scalar(
                select(AuditLog)
                .where(AuditLog.actor_id == "test-readiness-admin")
                .where(AuditLog.action == "dashboard.institutional_readiness_viewed")
            )
            assert audit_log is not None
    finally:
        app.dependency_overrides.clear()


def test_dashboard_export_csv_writes_audit_log_for_admin() -> None:
    admin_user = SimpleNamespace(id="test-admin-user", role="admin", is_active=True)
    app.dependency_overrides[get_current_user] = lambda: admin_user

    try:
        with TestClient(app) as client:
            response = client.get("/api/v1/dashboard/export.csv")

        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/csv")

        with SessionLocal() as db:
            audit_log = db.scalar(
                select(AuditLog)
                .where(AuditLog.actor_id == "test-admin-user")
                .where(AuditLog.action == "dashboard.export_csv")
            )
            assert audit_log is not None
            assert audit_log.entity == "dashboard"
            assert audit_log.details["format"] == "csv"
    finally:
        app.dependency_overrides.clear()
