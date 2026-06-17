from fastapi.testclient import TestClient

from app.db.session import SessionLocal
from app.main import app
from app.models_audit import AuditLog


def test_supervision_logs_requires_admin_auth() -> None:
    with TestClient(app) as client:
        response = client.get("/api/v1/supervision/audit-logs")

    assert response.status_code == 401


def test_admin_can_export_audit_logs_csv() -> None:
    with TestClient(app) as client:
        register_response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "audit-export-admin@coderoute.gn",
                "full_name": "Audit Export Admin",
                "password": "StrongPass123",
                "role": "admin",
            },
        )
        assert register_response.status_code in {201, 409}
        token = client.post(
            "/api/v1/auth/login",
            data={"username": "audit-export-admin@coderoute.gn", "password": "StrongPass123"},
        ).json()["access_token"]

        db = SessionLocal()
        try:
            db.add(AuditLog(action="audit.export.test", entity="audit", details={"scope": "test"}))
            db.commit()
        finally:
            db.close()

        response = client.get(
            "/api/v1/supervision/audit-logs/export.csv?entity=audit",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert "created_at,actor_id,action,entity,entity_id,details" in response.text
    assert "audit.export.test" in response.text
