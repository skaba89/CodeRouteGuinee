from datetime import UTC, datetime, timedelta
from uuid import uuid4

from fastapi.testclient import TestClient

from app.db.session import init_db
from app.main import app


def _auth_headers(client: TestClient, role: str) -> dict[str, str]:
    init_db()
    suffix = uuid4().hex
    email = f"{role}-submission-e2e-{suffix}@coderoute.local"
    password = "AdminPass123!"

    register_response = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "full_name": f"{role.title()} Submission E2E",
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


def test_candidate_submission_lifecycle_and_admin_handling() -> None:
    suffix = uuid4().hex[:8]

    with TestClient(app) as client:
        admin_headers = _auth_headers(client, "admin")
        center_headers = _auth_headers(client, "center")

        center_response = client.post(
            "/api/v1/centers",
            headers=admin_headers,
            json={
                "code": f"CTR-SUB-{suffix}",
                "name": "Centre Submission E2E",
                "city": "Conakry",
                "address": "Kipe",
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
                "starts_at": (datetime.now(UTC) + timedelta(days=9)).isoformat(),
                "capacity": 20,
            },
        )
        assert session_response.status_code == 201
        session = session_response.json()

        candidate_response = client.post(
            "/api/v1/candidates",
            headers=admin_headers,
            json={
                "first_name": "Fatoumata",
                "last_name": f"Submission-{suffix}",
                "identity_number": f"ID-SUB-{suffix}",
                "phone": "+224627000001",
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

        submission_response = client.post(
            "/api/v1/candidate-submissions",
            headers=admin_headers,
            json={
                "candidate_id": candidate["id"],
                "attempt_id": attempt["id"],
                "category": "review",
                "message": "Je souhaite que mon dossier soit examine par l'administration.",
            },
        )
        assert submission_response.status_code == 201
        submission = submission_response.json()
        assert submission["candidate_id"] == candidate["id"]
        assert submission["attempt_id"] == attempt["id"]
        assert submission["status"] == "submitted"

        list_response = client.get(
            f"/api/v1/candidate-submissions?candidate_id={candidate['id']}",
            headers=admin_headers,
        )
        assert list_response.status_code == 200
        items = list_response.json()
        assert any(item["id"] == submission["id"] for item in items)

        handle_response = client.post(
            f"/api/v1/candidate-submissions/{submission['id']}/handle",
            headers=admin_headers,
            json={
                "status": "accepted",
                "admin_response": "Votre dossier a ete accepte pour une verification complementaire.",
            },
        )
        assert handle_response.status_code == 200
        handled = handle_response.json()
        assert handled["status"] == "accepted"
        assert handled["admin_response"]
        assert handled["handled_by_id"]
        assert handled["handled_at"]

        audit_response = client.get(
            "/api/v1/supervision/audit-logs?action=candidate_submission.accepted&limit=25",
            headers=admin_headers,
        )
        assert audit_response.status_code == 200
        logs = audit_response.json()["items"]
        assert any(log["details"]["attempt_id"] == attempt["id"] for log in logs)
