from datetime import datetime, timedelta, UTC
from uuid import uuid4

from fastapi.testclient import TestClient

from app.db.session import init_db
from app.main import app


def _auth_headers(client: TestClient, role: str) -> dict[str, str]:
    init_db()
    suffix = uuid4().hex
    email = f"{role}-device-e2e-{suffix}@coderoute.local"
    password = "AdminPass123!"

    register_response = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "full_name": f"{role.title()} Device E2E",
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
            "last_name": f"Device-{suffix}",
            "identity_number": f"ID-DEV-{suffix}-{index}",
            "phone": f"+22462399{index:04d}",
            "permit_category": "B",
        },
    )
    assert response.status_code == 201
    return response.json()


def test_device_session_duplicate_detection_end_to_end() -> None:
    suffix = uuid4().hex[:8]
    device_key = f"CENTER-PC-{suffix}-01"

    with TestClient(app) as client:
        admin_headers = _auth_headers(client, "admin")
        center_headers = _auth_headers(client, "center")

        center_response = client.post(
            "/api/v1/centers",
            headers=admin_headers,
            json={
                "code": f"CTR-DEV-{suffix}",
                "name": "Centre Device E2E",
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
                "starts_at": (datetime.now(UTC) + timedelta(days=5)).isoformat(),
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

        first_heartbeat_response = client.post(
            "/api/v1/device-sessions/heartbeat",
            headers=center_headers,
            json={
                "center_id": center["id"],
                "session_id": session["id"],
                "attempt_id": attempt_one["id"],
                "device_key": device_key,
                "device_label": "Poste examen 01",
                "ip_address": "10.10.0.11",
                "user_agent": "CodeRouteExamBrowser/1.0",
            },
        )
        assert first_heartbeat_response.status_code == 201
        first_heartbeat = first_heartbeat_response.json()
        assert first_heartbeat["status"] == "active"

        second_heartbeat_response = client.post(
            "/api/v1/device-sessions/heartbeat",
            headers=center_headers,
            json={
                "center_id": center["id"],
                "session_id": session["id"],
                "attempt_id": attempt_two["id"],
                "device_key": device_key,
                "device_label": "Poste examen 01",
                "ip_address": "10.10.0.11",
                "user_agent": "CodeRouteExamBrowser/1.0",
            },
        )
        assert second_heartbeat_response.status_code == 201
        second_heartbeat = second_heartbeat_response.json()
        assert second_heartbeat["status"] == "suspicious"
        assert second_heartbeat["risk_reason"] == "same_device_key_used_for_multiple_attempts"

        alerts_response = client.get(
            f"/api/v1/device-sessions/alerts?session_id={session['id']}",
            headers=admin_headers,
        )
        assert alerts_response.status_code == 200
        alerts = alerts_response.json()
        assert len(alerts) >= 2
        assert any(alert["device_key"] == device_key for alert in alerts)

        audit_response = client.get(
            "/api/v1/supervision/audit-logs?action=device_session.suspicious_duplicate&limit=25",
            headers=admin_headers,
        )
        assert audit_response.status_code == 200
        audit_logs = audit_response.json()["items"]
        assert any(log["details"]["device_key"] == device_key for log in audit_logs)


def test_start_exam_from_booking_registers_device_session_and_duplicate_alert() -> None:
    suffix = uuid4().hex[:8]
    device_key = f"EXAM-START-{suffix}-01"

    with TestClient(app) as client:
        admin_headers = _auth_headers(client, "admin")
        center_headers = _auth_headers(client, "center")
        headers = admin_headers

        center_response = client.post(
            "/api/v1/centers",
            headers=admin_headers,
            json={
                "code": f"CTR-START-{suffix}",
                "name": "Centre Start Device",
                "city": "Conakry",
                "address": "Kaloum",
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
                "starts_at": (datetime.now(UTC) + timedelta(days=5)).isoformat(),
                "capacity": 20,
            },
        )
        assert session_response.status_code == 201
        session = session_response.json()

        candidate_one = _create_candidate(client, suffix, 11, admin_headers)
        candidate_two = _create_candidate(client, suffix, 12, admin_headers)

        booking_one_response = client.post("/api/v1/bookings", headers=headers, json={"candidate_id": candidate_one["id"], "session_id": session["id"]})
        booking_two_response = client.post("/api/v1/bookings", headers=headers, json={"candidate_id": candidate_two["id"], "session_id": session["id"]})
        assert booking_one_response.status_code == 201
        assert booking_two_response.status_code == 201
        booking_one = booking_one_response.json()
        booking_two = booking_two_response.json()

        first_attempt_response = client.post(
            "/api/v1/exams/start-from-booking",
            headers=center_headers,
            json={
                "booking_reference": booking_one["reference"],
                "device_key": device_key,
                "device_label": "Poste officiel 01",
            },
        )
        assert first_attempt_response.status_code == 201

        second_attempt_response = client.post(
            "/api/v1/exams/start-from-booking",
            headers=center_headers,
            json={
                "booking_reference": booking_two["reference"],
                "device_key": device_key,
                "device_label": "Poste officiel 01",
            },
        )
        assert second_attempt_response.status_code == 201

        alerts_response = client.get(
            f"/api/v1/device-sessions/alerts?session_id={session['id']}",
            headers=admin_headers,
        )
        assert alerts_response.status_code == 200
        alerts = alerts_response.json()
        assert any(alert["device_key"] == device_key and alert["risk_reason"] == "same_device_key_used_for_multiple_attempts" for alert in alerts)

        audit_response = client.get(
            "/api/v1/supervision/audit-logs?action=exam.device_session_suspicious&limit=25",
            headers=admin_headers,
        )
        assert audit_response.status_code == 200
        assert any(log["details"]["device_key"] == device_key for log in audit_response.json()["items"])
