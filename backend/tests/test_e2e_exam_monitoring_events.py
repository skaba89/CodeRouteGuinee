from datetime import datetime, timedelta, UTC
from uuid import uuid4

from fastapi.testclient import TestClient

from app.db.session import init_db
from app.main import app


def _auth_headers(client: TestClient, role: str) -> dict[str, str]:
    init_db()
    suffix = uuid4().hex
    email = f"{role}-monitoring-e2e-{suffix}@coderoute.local"
    password = "AdminPass123!"

    register_response = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "full_name": f"{role.title()} Monitoring E2E",
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


def test_exam_monitoring_events_risk_summary_and_audit_log() -> None:
    suffix = uuid4().hex[:8]

    with TestClient(app) as client:
        admin_headers = _auth_headers(client, "admin")
        center_headers = _auth_headers(client, "center")

        center_response = client.post(
            "/api/v1/centers",
            headers=admin_headers,
            json={
                "code": f"CTR-MON-{suffix}",
                "name": "Centre Monitoring E2E",
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
                "starts_at": (datetime.now(UTC) + timedelta(days=6)).isoformat(),
                "capacity": 20,
            },
        )
        assert session_response.status_code == 201
        session = session_response.json()

        candidate_response = client.post(
            "/api/v1/candidates",
            headers=admin_headers,
            json={
                "first_name": "Aminata",
                "last_name": f"Monitoring-{suffix}",
                "identity_number": f"ID-MON-{suffix}",
                "phone": "+224624000001",
                "permit_category": "B",
            },
        )
        assert candidate_response.status_code == 201
        candidate = candidate_response.json()

        attempt_response = client.post(
            "/api/v1/exams/start",
            headers=center_headers,
            json={"candidate_id": candidate["id"], "session_id": session["id"]},
        )
        assert attempt_response.status_code == 201
        attempt = attempt_response.json()

        low_event_response = client.post(
            "/api/v1/exam-monitoring/events",
            headers=center_headers,
            json={
                "attempt_id": attempt["id"],
                "event_type": "heartbeat_delay",
                "severity": "low",
                "details": {"delay_seconds": 4},
            },
        )
        assert low_event_response.status_code == 201
        assert low_event_response.json()["risk_score"] == 1

        high_event_response = client.post(
            "/api/v1/exam-monitoring/events",
            headers=center_headers,
            json={
                "attempt_id": attempt["id"],
                "event_type": "fullscreen_exit",
                "severity": "high",
                "details": {"duration_seconds": 12},
            },
        )
        assert high_event_response.status_code == 201
        high_event = high_event_response.json()
        assert high_event["risk_score"] == 7

        summary_response = client.get(
            f"/api/v1/exam-monitoring/attempts/{attempt['id']}/summary",
            headers=admin_headers,
        )
        assert summary_response.status_code == 200
        summary = summary_response.json()
        assert summary["attempt_id"] == attempt["id"]
        assert summary["total_events"] == 2
        assert summary["total_risk_score"] == 8
        assert summary["max_severity"] == "high"
        assert summary["status"] == "watch"

        events_response = client.get(
            f"/api/v1/exam-monitoring/events?attempt_id={attempt['id']}",
            headers=admin_headers,
        )
        assert events_response.status_code == 200
        events = events_response.json()
        assert len(events) == 2
        assert any(event["event_type"] == "fullscreen_exit" for event in events)

        audit_response = client.get(
            "/api/v1/supervision/audit-logs?action=exam_monitoring.high_risk_event&limit=25",
            headers=admin_headers,
        )
        assert audit_response.status_code == 200
        audit_logs = audit_response.json()
        assert any(log["details"]["attempt_id"] == attempt["id"] for log in audit_logs)
