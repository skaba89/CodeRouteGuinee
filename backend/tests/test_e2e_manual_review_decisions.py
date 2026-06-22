from datetime import datetime, timedelta, UTC
from uuid import uuid4

from fastapi.testclient import TestClient

from app.db.session import init_db
from app.main import app


def _auth_headers(client: TestClient, role: str) -> dict[str, str]:
    init_db()
    suffix = uuid4().hex
    email = f"{role}-review-e2e-{suffix}@coderoute.local"
    password = "AdminPass123!"

    register_response = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "full_name": f"{role.title()} Review E2E",
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


def test_manual_review_decision_updates_attempt_and_audit_log() -> None:
    suffix = uuid4().hex[:8]

    with TestClient(app) as client:
        admin_headers = _auth_headers(client, "admin")
        center_headers = _auth_headers(client, "center")

        center_response = client.post(
            "/api/v1/centers",
            headers=admin_headers,
            json={
                "code": f"CTR-REV-{suffix}",
                "name": "Centre Review E2E",
                "city": "Conakry",
                "address": "Ratoma",
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
                "starts_at": (datetime.now(UTC) + timedelta(days=8)).isoformat(),
                "capacity": 20,
            },
        )
        assert session_response.status_code == 201
        session = session_response.json()

        candidate_response = client.post(
            "/api/v1/candidates",
            headers=admin_headers,
            json={
                "first_name": "Mamadou",
                "last_name": f"Review-{suffix}",
                "identity_number": f"ID-REV-{suffix}",
                "phone": "+224626000001",
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
        assert attempt["status"] == "started"

        monitoring_response = client.post(
            "/api/v1/exam-monitoring/events",
            headers=center_headers,
            json={
                "attempt_id": attempt["id"],
                "event_type": "tab_switch",
                "severity": "critical",
                "details": {"count": 3},
            },
        )
        assert monitoring_response.status_code == 201

        case_response = client.get(
            f"/api/v1/exam-reviews/attempts/{attempt['id']}",
            headers=admin_headers,
        )
        assert case_response.status_code == 200
        review_case = case_response.json()
        assert review_case["attempt_id"] == attempt["id"]
        assert review_case["monitoring_events"] == 1
        assert review_case["monitoring_risk_score"] == 12
        assert review_case["review_status"] == "manual_review_pending"

        decision_response = client.post(
            "/api/v1/exam-reviews/decisions",
            headers=admin_headers,
            json={
                "attempt_id": attempt["id"],
                "decision": "invalidate",
                "reason": "Evenement critique confirme par le superviseur",
            },
        )
        assert decision_response.status_code == 201
        decision = decision_response.json()
        assert decision["decision"] == "invalidate"
        assert decision["previous_attempt_status"] == "started"
        assert decision["new_attempt_status"] == "invalidated"

        reviewed_case_response = client.get(
            f"/api/v1/exam-reviews/attempts/{attempt['id']}",
            headers=admin_headers,
        )
        assert reviewed_case_response.status_code == 200
        reviewed_case = reviewed_case_response.json()
        assert reviewed_case["current_status"] == "invalidated"
        assert reviewed_case["review_status"] == "invalidate"
        assert reviewed_case["last_decision"]["id"] == decision["id"]

        decisions_response = client.get(
            f"/api/v1/exam-reviews/decisions?attempt_id={attempt['id']}",
            headers=admin_headers,
        )
        assert decisions_response.status_code == 200
        decisions = decisions_response.json()
        assert any(item["id"] == decision["id"] for item in decisions)

        audit_response = client.get(
            "/api/v1/supervision/audit-logs?action=exam_review.invalidate&limit=25",
            headers=admin_headers,
        )
        assert audit_response.status_code == 200
        audit_logs = audit_response.json()["items"]
        assert any(log["details"]["attempt_id"] == attempt["id"] for log in audit_logs)
