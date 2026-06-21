from datetime import UTC, datetime, timedelta
from uuid import uuid4

from fastapi.testclient import TestClient

from app.db.session import init_db
from app.main import app
from app.routers import auth as _auth_module
from tests.conftest import TEST_BOOTSTRAP_TOKEN


def _auth_headers(client: TestClient, role: str) -> dict[str, str]:
    init_db()
    suffix = uuid4().hex
    email = f"{role}-station-e2e-{suffix}@coderoute.local"
    password = "AdminPass123!"

    _auth_module.settings.admin_registration_token = TEST_BOOTSTRAP_TOKEN
    register_response = client.post(
        "/api/v1/auth/register",
        headers={"X-Admin-Registration-Token": TEST_BOOTSTRAP_TOKEN},
        json={
            "email": email,
            "full_name": f"{role.title()} Station E2E",
            "password": password,
            "role": role,
        },
    )
    assert register_response.status_code == 201

    login_response = client.post(
        "/api/v1/auth/login",
        data={"username": email, "password": password},
    )
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _create_candidate(client: TestClient, suffix: str, index: int, headers: dict) -> dict:
    response = client.post(
        "/api/v1/candidates",
        headers=headers,
            json={
            "first_name": f"Candidat{index}",
            "last_name": f"Station-{suffix}",
            "identity_number": f"ID-ST-{suffix}-{index}",
            "phone": f"+22462811{index:04d}",
            "permit_category": "B",
        },
    )
    assert response.status_code == 201
    return response.json()


def test_center_station_registry_flags_unknown_device_keys() -> None:
    suffix = uuid4().hex[:8]
    known_device_key = f"CENTER-{suffix}-POSTE-01"
    unknown_device_key = f"CENTER-{suffix}-UNKNOWN-99"

    with TestClient(app) as client:
        admin_headers = _auth_headers(client, "admin")
        center_headers = _auth_headers(client, "center")

        center_response = client.post(
            "/api/v1/centers",
            headers=admin_headers,
            json={
                "code": f"CTR-ST-{suffix}",
                "name": "Centre Stations E2E",
                "city": "Conakry",
                "address": "Dixinn",
                "capacity": 20,
                "status": "accredited",
            },
        )
        assert center_response.status_code == 201
        center = center_response.json()

        session_response = client.post(
            "/api/v1/sessions",
            headers=admin_headers,
            json={
                "center_id": center["id"],
                "starts_at": (datetime.now(UTC) + timedelta(days=10)).isoformat(),
                "capacity": 20,
            },
        )
        assert session_response.status_code == 201
        session = session_response.json()

        station_response = client.post(
            "/api/v1/center-stations",
            headers=admin_headers,
            json={
                "center_id": center["id"],
                "device_key": known_device_key,
                "label": "Poste 01",
                "room": "Salle A",
                "status": "active",
            },
        )
        assert station_response.status_code == 201
        station = station_response.json()
        assert station["device_key"] == known_device_key
        assert station["status"] == "active"

        candidate_one = _create_candidate(client, suffix, 1, admin_headers)
        candidate_two = _create_candidate(client, suffix, 2, admin_headers)

        attempt_one_response = client.post(
            "/api/v1/exams/start",
            headers=center_headers,
            json={"candidate_id": candidate_one["id"], "session_id": session["id"]},
        )
        assert attempt_one_response.status_code == 201
        attempt_one = attempt_one_response.json()

        attempt_two_response = client.post(
            "/api/v1/exams/start",
            headers=center_headers,
            json={"candidate_id": candidate_two["id"], "session_id": session["id"]},
        )
        assert attempt_two_response.status_code == 201
        attempt_two = attempt_two_response.json()

        known_heartbeat = client.post(
            "/api/v1/device-sessions/heartbeat",
            headers=center_headers,
            json={
                "center_id": center["id"],
                "session_id": session["id"],
                "attempt_id": attempt_one["id"],
                "device_key": known_device_key,
                "device_label": "Poste 01",
            },
        )
        assert known_heartbeat.status_code == 201
        assert known_heartbeat.json()["status"] == "active"
        assert known_heartbeat.json()["risk_reason"] is None

        unknown_heartbeat = client.post(
            "/api/v1/device-sessions/heartbeat",
            headers=center_headers,
            json={
                "center_id": center["id"],
                "session_id": session["id"],
                "attempt_id": attempt_two["id"],
                "device_key": unknown_device_key,
                "device_label": "Poste inconnu",
            },
        )
        assert unknown_heartbeat.status_code == 201
        unknown_session = unknown_heartbeat.json()
        assert unknown_session["status"] == "suspicious"
        assert unknown_session["risk_reason"] == "unregistered_center_station"

        alerts_response = client.get(
            f"/api/v1/device-sessions/alerts?center_id={center['id']}",
            headers=admin_headers,
        )
        assert alerts_response.status_code == 200
        alerts = alerts_response.json()
        assert any(item["device_key"] == unknown_device_key for item in alerts)

        audit_response = client.get(
            "/api/v1/supervision/audit-logs?action=device_session.station_alert&limit=25",
            headers=admin_headers,
        )
        assert audit_response.status_code == 200
        logs = audit_response.json()
        assert any(log["details"]["device_key"] == unknown_device_key for log in logs)
