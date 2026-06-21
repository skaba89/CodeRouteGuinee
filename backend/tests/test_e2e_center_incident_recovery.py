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
    email = f"{role}-incident-e2e-{suffix}@coderoute.local"
    password = "AdminPass123!"

    _auth_module.settings.admin_registration_token = TEST_BOOTSTRAP_TOKEN
    register_response = client.post(
        "/api/v1/auth/register",
        headers={"X-Admin-Registration-Token": TEST_BOOTSTRAP_TOKEN},
        json={
            "email": email,
            "full_name": f"{role.title()} Incident E2E",
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


def test_center_incident_blocks_attempt_and_allows_retake() -> None:
    suffix = uuid4().hex[:8]

    with TestClient(app) as client:
        admin_headers = _auth_headers(client, "admin")
        center_headers = _auth_headers(client, "center")
        headers = admin_headers

        center_response = client.post(
            "/api/v1/centers",
            headers=admin_headers,
            json={
                "code": f"CTR-INC-{suffix}",
                "name": "Centre Incident E2E",
                "city": "Conakry",
                "address": "Ratoma",
                "capacity": 30,
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
                "starts_at": (datetime.now(UTC) + timedelta(days=3)).isoformat(),
                "capacity": 30,
            },
        )
        assert session_response.status_code == 201
        session = session_response.json()

        for index in range(40):
            question_response = client.post(
                "/api/v1/questions",
                headers=admin_headers,
                json={
                    "category": "priorite",
                    "text": f"Question incident {suffix}-{index}",
                    "options": ["A", "B", "C"],
                    "correct_answer": "A",
                    "explanation": "Reponse de test incident",
                },
            )
            assert question_response.status_code == 201

        candidate_response = client.post(
            "/api/v1/candidates",
            headers=admin_headers,
            json={
                "first_name": "Fatoumata",
                "last_name": "Camara",
                "identity_number": f"ID-INC-{suffix}",
                "phone": "+224623111222",
                "permit_category": "B",
            },
        )
        assert candidate_response.status_code == 201
        candidate = candidate_response.json()

        start_response = client.post(
            "/api/v1/exams/start",
            headers=center_headers,
            json={"candidate_id": candidate["id"], "session_id": session["id"]},
        )
        assert start_response.status_code == 201
        initial_attempt = start_response.json()
        assert initial_attempt["status"] == "started"

        incident_response = client.post(
            "/api/v1/center-incidents",
            headers=center_headers,
            json={
                "center_id": center["id"],
                "session_id": session["id"],
                "attempt_id": initial_attempt["id"],
                "incident_type": "power_cut",
                "severity": "high",
                "description": "Coupure de courant pendant l'examen du candidat.",
            },
        )
        assert incident_response.status_code == 201
        incident = incident_response.json()
        assert incident["status"] == "open"
        assert incident["attempt_id"] == initial_attempt["id"]

        blocked_submit_response = client.post(
            f"/api/v1/exams/{initial_attempt['id']}/submit",
            headers=center_headers,
            json={"answers": {}},
        )
        assert blocked_submit_response.status_code == 409
        assert blocked_submit_response.json()["detail"] == "Exam attempt is not active"

        resolve_response = client.post(
            f"/api/v1/center-incidents/{incident['id']}/resolve",
            headers=admin_headers,
            json={
                "resolution_notes": "Incident confirme par le superviseur. Nouvelle tentative autorisee.",
                "allow_retake": True,
            },
        )
        assert resolve_response.status_code == 200
        resolved_incident = resolve_response.json()
        assert resolved_incident["status"] == "resolved"
        assert resolved_incident["new_attempt_id"]
        assert resolved_incident["new_attempt_id"] != initial_attempt["id"]

        questions_response = client.get("/api/v1/questions", headers=headers)
        assert questions_response.status_code == 200
        answers = {question["id"]: question["correct_answer"] for question in questions_response.json()}
        assert len(answers) >= 40

        new_attempt_id = resolved_incident["new_attempt_id"]
        submit_response = client.post(
            f"/api/v1/exams/{new_attempt_id}/submit",
            headers=center_headers,
            json={"answers": answers},
        )
        assert submit_response.status_code == 200
        submitted_attempt = submit_response.json()
        assert submitted_attempt["id"] == new_attempt_id
        assert submitted_attempt["status"] == "submitted"
        assert submitted_attempt["passed"] is True

        incidents_response = client.get("/api/v1/center-incidents?status_filter=resolved", headers=admin_headers)
        assert incidents_response.status_code == 200
        assert any(item["id"] == incident["id"] for item in incidents_response.json())

        audit_response = client.get(
            "/api/v1/supervision/audit-logs?action=center_incident.resolved&limit=25",
            headers=admin_headers,
        )
        assert audit_response.status_code == 200
        assert any(log["entity_id"] == incident["id"] for log in audit_response.json())
