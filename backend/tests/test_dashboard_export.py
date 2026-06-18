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


def test_institutional_report_requires_authentication() -> None:
    with TestClient(app) as client:
        response = client.get("/api/v1/dashboard/institutional-report")

    assert response.status_code == 401


def test_institutional_report_pdf_requires_authentication() -> None:
    with TestClient(app) as client:
        response = client.get("/api/v1/dashboard/institutional-report.pdf")

    assert response.status_code == 401


def test_institutional_action_center_requires_authentication() -> None:
    with TestClient(app) as client:
        response = client.get("/api/v1/dashboard/institutional-action-center")

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


def test_institutional_report_returns_national_summary_for_admin() -> None:
    admin_user = SimpleNamespace(id="test-report-admin", role="admin", is_active=True)
    app.dependency_overrides[get_current_user] = lambda: admin_user

    try:
        with TestClient(app) as client:
            response = client.get("/api/v1/dashboard/institutional-report")

        assert response.status_code == 200
        payload = response.json()
        assert payload["generated_for"] == "Etat guineen - dossier CodeRoute Guinee"
        assert 0 <= payload["readiness_score"] <= 100
        assert isinstance(payload["centers_by_status"], dict)
        assert isinstance(payload["questions_by_status"], dict)
        assert isinstance(payload["identity_checks_by_status"], dict)
        assert isinstance(payload["authorizations_by_status"], dict)
        assert payload["recommendations"]

        with SessionLocal() as db:
            audit_log = db.scalar(
                select(AuditLog)
                .where(AuditLog.actor_id == "test-report-admin")
                .where(AuditLog.action == "dashboard.institutional_report_viewed")
            )
            assert audit_log is not None
    finally:
        app.dependency_overrides.clear()


def test_institutional_action_center_returns_priorities_for_admin() -> None:
    admin_user = SimpleNamespace(id="test-action-center-admin", role="admin", is_active=True)
    app.dependency_overrides[get_current_user] = lambda: admin_user

    try:
        with TestClient(app) as client:
            response = client.get("/api/v1/dashboard/institutional-action-center")

        assert response.status_code == 200
        payload = response.json()
        assert payload["total_actions"] >= 0
        assert payload["critical_actions"] >= 0
        assert isinstance(payload["items"], list)
        for item in payload["items"]:
            assert item["code"]
            assert item["label"]
            assert item["target"].startswith("#")
            assert item["severity"] in {"normal", "warning", "critical"}

        with SessionLocal() as db:
            audit_log = db.scalar(
                select(AuditLog)
                .where(AuditLog.actor_id == "test-action-center-admin")
                .where(AuditLog.action == "dashboard.institutional_action_center_viewed")
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


def test_institutional_report_csv_writes_audit_log_for_admin() -> None:
    admin_user = SimpleNamespace(id="test-report-csv-admin", role="admin", is_active=True)
    app.dependency_overrides[get_current_user] = lambda: admin_user

    try:
        with TestClient(app) as client:
            response = client.get("/api/v1/dashboard/institutional-report.csv")

        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/csv")
        assert "section;key;value" in response.text
        assert "summary;generated_for;Etat guineen - dossier CodeRoute Guinee" in response.text

        with SessionLocal() as db:
            audit_log = db.scalar(
                select(AuditLog)
                .where(AuditLog.actor_id == "test-report-csv-admin")
                .where(AuditLog.action == "dashboard.institutional_report_export_csv")
            )
            assert audit_log is not None
            assert audit_log.entity == "dashboard"
    finally:
        app.dependency_overrides.clear()


def test_institutional_report_pdf_writes_audit_log_for_admin() -> None:
    admin_user = SimpleNamespace(id="test-report-pdf-admin", role="admin", is_active=True)
    app.dependency_overrides[get_current_user] = lambda: admin_user

    try:
        with TestClient(app) as client:
            response = client.get("/api/v1/dashboard/institutional-report.pdf")

        assert response.status_code == 200
        assert response.headers["content-type"] == "application/pdf"
        assert "coderoute-institutional-report.pdf" in response.headers["content-disposition"]
        assert response.content.startswith(b"%PDF")
        assert b"Rapport institutionnel" in response.content

        with SessionLocal() as db:
            audit_log = db.scalar(
                select(AuditLog)
                .where(AuditLog.actor_id == "test-report-pdf-admin")
                .where(AuditLog.action == "dashboard.institutional_report_export_pdf")
            )
            assert audit_log is not None
            assert audit_log.entity == "dashboard"
            assert audit_log.details["recommendations"] >= 0
    finally:
        app.dependency_overrides.clear()
