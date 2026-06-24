from datetime import UTC, datetime, timedelta
from uuid import uuid4

from fastapi.testclient import TestClient

from app.db.session import init_db
from app.main import app
from tests.conftest import get_admin_headers, get_center_headers


def _auth_headers(client: TestClient, role: str) -> dict[str, str]:
    init_db()
    suffix = uuid4().hex
    email = f"{role}-antifraud-e2e-{suffix}@coderoute.local"
    password = "AdminPass123!"

    register_response = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "full_name": f"{role.title()} AntiFraud E2E",
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
            "last_name": f"AntiFraud-{suffix}",
            "identity_number": f"ID-AF-{suffix}-{index}",
            "phone": f"+22462599{index:04d}",
            "permit_category": "B",
        },
    )
    assert response.status_code == 201
    return response.json()


def test_national_antifraud_dashboard_aggregates_risk_signals() -> None:
    suffix = uuid4().hex[:8]
    device_key = f"AF-PC-{suffix}-01"

    with TestClient(app) as client:
        admin_headers = get_admin_headers(client)
        center_headers = get_center_headers(client)
        admin_headers = _auth_headers(client, "admin")
        center_headers = _auth_headers(client, "center")

        center_response = client.post(
            "/api/v1/centers",
            headers=admin_headers,
            json={
                "code": f"CTR-AF-{suffix}",
                "name": "Centre AntiFraud E2E",
                "city": "Conakry",
                "address": "Matoto",
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
                "starts_at": (datetime.now(UTC) + timedelta(days=7)).isoformat(),
                "capacity": 20,
            },
        )
        assert session_response.status_code == 201
        session = session_response.json()

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

        incident_response = client.post(
            "/api/v1/center-incidents",
            headers=center_headers,
            json={
                "center_id": center["id"],
                "session_id": session["id"],
                "attempt_id": attempt_one["id"],
                "incident_type": "supervision_alert",
                "severity": "high",
                "description": "Alerte superviseur pendant la session",
            },
        )
        assert incident_response.status_code == 201

        first_device_response = client.post(
            "/api/v1/device-sessions/heartbeat",
            headers=center_headers,
            json={
                "center_id": center["id"],
                "session_id": session["id"],
                "attempt_id": attempt_one["id"],
                "device_key": device_key,
                "device_label": "Poste 01",
            },
        )
        assert first_device_response.status_code == 201

        second_device_response = client.post(
            "/api/v1/device-sessions/heartbeat",
            headers=center_headers,
            json={
                "center_id": center["id"],
                "session_id": session["id"],
                "attempt_id": attempt_two["id"],
                "device_key": device_key,
                "device_label": "Poste 01",
            },
        )
        assert second_device_response.status_code == 201
        assert second_device_response.json()["status"] == "suspicious"

        monitoring_response = client.post(
            "/api/v1/exam-monitoring/events",
            headers=center_headers,
            json={
                "attempt_id": attempt_one["id"],
                "event_type": "tab_switch",
                "severity": "high",
                "details": {"duration_seconds": 9},
            },
        )
        assert monitoring_response.status_code == 201

        dashboard_response = client.get("/api/v1/dashboard/anti-fraud?limit=2000", headers=admin_headers)
        assert dashboard_response.status_code == 200
        dashboard = dashboard_response.json()

        assert dashboard["open_center_incidents"] >= 1
        assert dashboard["suspicious_device_sessions"] >= 2
        assert dashboard["high_risk_monitoring_events"] >= 1
        assert dashboard["total_monitoring_risk_score"] >= 7
        assert dashboard["centers_at_risk"]

        matching = [row for row in dashboard["centers_at_risk"] if row["center_id"] == center["id"]]
        assert matching, (
            f"Centre {center['id']} absent de centers_at_risk "
            f"(total: {len(dashboard['centers_at_risk'])}, "
            f"5 premiers: {[r['center_id'] for r in dashboard['centers_at_risk'][:5]]})"
        )
        risk_center = matching[0]
        assert risk_center["center_code"] == center["code"]
        assert risk_center["open_incidents"] >= 1
        assert risk_center["suspicious_devices"] >= 2
        assert risk_center["monitoring_risk_score"] >= 7
        assert risk_center["total_risk_score"] >= 10  # >= 1 incident(5) + 1 high event(7) = 12 min
        assert risk_center["status"] in {"manual_review", "critical_review"}

        public_dashboard_response = client.get("/api/v1/dashboard", headers=admin_headers)
        assert public_dashboard_response.status_code == 200
        assert public_dashboard_response.json()["fraud_alerts"] >= 4
