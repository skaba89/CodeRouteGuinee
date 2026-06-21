from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db.session import SessionLocal
from app.main import app
from app.models_audit import AuditLog
from app.models_center import Center
from app.routers import auth as _auth_module
from tests.conftest import TEST_BOOTSTRAP_TOKEN


def _admin_headers(client: TestClient) -> dict[str, str]:
    suffix = str(uuid4())[:8]
    email = f"admin-center-{suffix}@coderoute.gn"
    password = "StrongPass123!"
    _auth_module.settings.admin_registration_token = TEST_BOOTSTRAP_TOKEN
    response = client.post(
        "/api/v1/auth/register",
        headers={"X-Admin-Registration-Token": TEST_BOOTSTRAP_TOKEN},
            json={"email": email, "full_name": "Admin Centre", "password": password, "role": "admin"},
    )
    assert response.status_code == 201
    token_response = client.post("/api/v1/auth/login", data={"username": email, "password": password})
    assert token_response.status_code == 200
    return {"Authorization": f"Bearer {token_response.json()['access_token']}"}


def test_center_status_update_requires_admin_authentication() -> None:
    with TestClient(app) as client:
        response = client.patch(
            "/api/v1/centers/unknown/status",
            json={"status": "suspended", "reason": "Controle administratif"},
        )

    assert response.status_code == 401


def test_center_official_import_requires_admin_authentication() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/centers/import-official",
            json={
                "source": "Ministere transports",
                "reason": "Import initial",
                "centers": [
                    {
                        "code": "OFF-001",
                        "name": "Centre officiel",
                        "city": "Conakry",
                        "address": "Kaloum",
                        "capacity": 20,
                        "status": "accredited",
                    }
                ],
            },
        )

    assert response.status_code == 401


def test_admin_can_import_official_centers_with_audit_log() -> None:
    with TestClient(app) as client:
        suffix = str(uuid4())[:8].upper()
        headers = _admin_headers(client)

        response = client.post(
            "/api/v1/centers/import-official",
            headers=headers,
            json={
                "source": "Liste officielle DNTT",
                "reason": "Chargement des centres pilotes",
                "centers": [
                    {
                        "code": f"IMP-{suffix}-1",
                        "name": "Centre Pilote Conakry",
                        "city": "Conakry",
                        "address": "Kaloum",
                        "capacity": 30,
                        "status": "accredited",
                    },
                    {
                        "code": f"IMP-{suffix}-2",
                        "name": "Centre Pilote Kindia",
                        "city": "Kindia",
                        "address": "Centre ville",
                        "capacity": 24,
                        "status": "pending_audit",
                    },
                ],
            },
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["imported"] == 2
        assert payload["created"] == 2
        assert payload["updated"] == 0

        update_response = client.post(
            "/api/v1/centers/import-official",
            headers=headers,
            json={
                "source": "Liste officielle DNTT",
                "reason": "Correction capacite",
                "centers": [
                    {
                        "code": f"imp-{suffix}-1",
                        "name": "Centre Pilote Conakry",
                        "city": "Conakry",
                        "address": "Kaloum",
                        "capacity": 35,
                        "status": "active",
                    }
                ],
            },
        )
        assert update_response.status_code == 200
        assert update_response.json()["updated"] == 1

        centers = client.get("/api/v1/centers", headers=headers).json()
        imported = next(center for center in centers if center["code"] == f"IMP-{suffix}-1")
        assert imported["capacity"] == 35
        assert imported["status"] == "active"

        with SessionLocal() as db:
            audit_log = db.scalar(
                select(AuditLog)
                .where(AuditLog.action == "center.official_import")
                .where(AuditLog.entity == "center")
                .order_by(AuditLog.created_at.desc())
            )
            assert audit_log is not None
            assert audit_log.details["source"] == "Liste officielle DNTT"
            assert audit_log.details["imported"] >= 1


def test_center_official_import_dry_run_does_not_write() -> None:
    with TestClient(app) as client:
        suffix = str(uuid4())[:8].upper()
        center_code = f"DRY-{suffix}"
        headers = _admin_headers(client)

        response = client.post(
            "/api/v1/centers/import-official",
            headers=headers,
            json={
                "source": "Liste officielle DNTT",
                "reason": "Simulation avant import",
                "dry_run": True,
                "centers": [
                    {
                        "code": center_code,
                        "name": "Centre Simulation",
                        "city": "Conakry",
                        "address": "Kaloum",
                        "capacity": 24,
                        "status": "pending_audit",
                    }
                ],
            },
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["dry_run"] is True
        assert payload["created"] == 1
        assert payload["updated"] == 0
        assert payload["codes"] == [center_code]

        with SessionLocal() as db:
            center = db.scalar(select(Center).where(Center.code == center_code))
            assert center is None


def test_center_official_import_rejects_duplicate_codes() -> None:
    with TestClient(app) as client:
        headers = _admin_headers(client)
        response = client.post(
            "/api/v1/centers/import-official",
            headers=headers,
            json={
                "source": "Liste officielle DNTT",
                "reason": "Doublon volontaire",
                "centers": [
                    {
                        "code": "DUP-CENTER",
                        "name": "Centre A",
                        "city": "Conakry",
                        "address": "Kaloum",
                        "capacity": 20,
                        "status": "active",
                    },
                    {
                        "code": "dup-center",
                        "name": "Centre B",
                        "city": "Conakry",
                        "address": "Dixinn",
                        "capacity": 20,
                        "status": "active",
                    },
                ],
            },
        )

    assert response.status_code == 422
    assert "DUP-CENTER" in str(response.json()["detail"])


def test_admin_can_accredit_and_suspend_center_with_audit_log() -> None:
    with TestClient(app) as client:
        suffix = str(uuid4())[:8]
        headers = _admin_headers(client)
        center_response = client.post(
            "/api/v1/centers",
            headers=headers,
            json={
                "code": f"GOV-{suffix}",
                "name": "Centre Gouvernance",
                "city": "Conakry",
                "address": "Kaloum",
                "capacity": 25,
                "status": "pending_audit",
            },
        )
        assert center_response.status_code == 201
        center = center_response.json()

        accredited_response = client.patch(
            f"/api/v1/centers/{center['id']}/status",
            headers=headers,
            json={"status": "accredited", "reason": "Audit institutionnel valide"},
        )
        assert accredited_response.status_code == 200
        assert accredited_response.json()["status"] == "accredited"

        suspended_response = client.patch(
            f"/api/v1/centers/{center['id']}/status",
            headers=headers,
            json={"status": "suspended", "reason": "Suspension administrative"},
        )
        assert suspended_response.status_code == 200
        assert suspended_response.json()["status"] == "suspended"

        with SessionLocal() as db:
            logs = db.scalars(
                select(AuditLog)
                .where(AuditLog.entity == "center")
                .where(AuditLog.entity_id == center["id"])
                .where(AuditLog.action == "center.status_updated")
            ).all()
            assert len(logs) >= 2
            assert any(log.details["new_status"] == "suspended" for log in logs)
