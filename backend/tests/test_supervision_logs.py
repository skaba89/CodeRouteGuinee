from fastapi.testclient import TestClient

from app.db.session import SessionLocal
from app.main import app
from app.models_audit import AuditLog


def test_supervision_logs_requires_admin_auth() -> None:
    with TestClient(app) as client:
        response = client.get("/api/v1/supervision/audit-logs")

    assert response.status_code == 401


def test_admin_can_export_audit_logs_csv() -> None:
    from tests.conftest import get_admin_headers
    with TestClient(app) as client:
        headers = get_admin_headers(client)

        db = SessionLocal()
        try:
            db.add(AuditLog(action="audit.export.test", entity="audit", details={"scope": "test"}))
            db.commit()
        finally:
            db.close()

        response = client.get(
            "/api/v1/supervision/audit-logs/export.csv?entity=audit",
            headers=headers,
        )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert "created_at,actor_id,action,entity,entity_id,details" in response.text
    assert "audit.export.test" in response.text
