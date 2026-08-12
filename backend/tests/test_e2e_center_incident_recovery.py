from datetime import UTC, datetime, timedelta
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db.session import SessionLocal, init_db
from app.main import app
from app.models_exam_question_trace import ExamQuestionTrace
from app.models_question import Question
from tests.conftest import seed_media_ready_official_bank, verify_candidate_identity


def _auth_headers(client: TestClient, role: str) -> dict[str, str]:
    init_db()
    suffix = uuid4().hex
    email = f"{role}-incident-e2e-{suffix}@coderoute.local"
    password = "AdminPass123!"

    register_response = client.post(
        "/api/v1/auth/register",
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


def test_center_incident_blocks_attempt_and_creates_traced_official_retake() -> None:
    suffix = uuid4().hex[:8]

    with TestClient(app) as client:
        admin_headers = _auth_headers(client, "admin")
        super_headers = _auth_headers(client, "super_admin")

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

        seed_media_ready_official_bank(
            client,
            super_headers,
            marker=f"incident-{suffix}",
        )

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
        verify_candidate_identity(
            client,
            candidate["id"],
            admin_headers,
            marker=f"incident-{suffix}",
        )

        # L'admin national peut lancer la tentative sans dépendre de l'affectation
        # d'un compte centre : le test vise ici le workflow d'incident/rattrapage.
        start_response = client.post(
            "/api/v1/exams/start",
            headers=admin_headers,
            json={"candidate_id": candidate["id"], "session_id": session["id"]},
        )
        assert start_response.status_code == 201, start_response.text
        initial_attempt = start_response.json()
        assert initial_attempt["status"] == "started"

        with SessionLocal() as db:
            initial_trace = db.scalar(
                select(ExamQuestionTrace).where(
                    ExamQuestionTrace.attempt_id == initial_attempt["id"]
                )
            )
            assert initial_trace is not None
            assert initial_trace.question_count == 40

        incident_response = client.post(
            "/api/v1/center-incidents",
            headers=admin_headers,
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
            headers=admin_headers,
            json={"answers": {}},
        )
        assert blocked_submit_response.status_code == 409
        assert blocked_submit_response.json()["detail"] == "Exam attempt is not active"

        resolve_response = client.post(
            f"/api/v1/center-incidents/{incident['id']}/resolve",
            headers=admin_headers,
            json={
                "resolution_notes": "Incident confirmé par le superviseur. Nouvelle tentative autorisée.",
                "allow_retake": True,
            },
        )
        assert resolve_response.status_code == 200, resolve_response.text
        resolved_incident = resolve_response.json()
        assert resolved_incident["status"] == "resolved"
        assert resolved_incident["new_attempt_id"]
        assert resolved_incident["new_attempt_id"] != initial_attempt["id"]

        new_attempt_id = resolved_incident["new_attempt_id"]
        with SessionLocal() as db:
            new_trace = db.scalar(
                select(ExamQuestionTrace).where(
                    ExamQuestionTrace.attempt_id == new_attempt_id
                )
            )
            assert new_trace is not None
            assert new_trace.question_count == 40
            assert len(new_trace.question_ids) == 40
            assert new_trace.bank_hash
            assert "official-" in new_trace.version_label

        # Le nouvel examen doit être immédiatement exploitable par l'API fail-closed.
        q_resp = client.get(
            f"/api/v1/exams/{new_attempt_id}/questions",
            headers=admin_headers,
        )
        assert q_resp.status_code == 200
        exam_questions = q_resp.json()["questions"]
        assert len(exam_questions) == 40

        # La réussite du rattrapage doit utiliser la vraie clé de correction de
        # la trace, pas supposer que la première option est toujours correcte.
        with SessionLocal() as db:
            trace = db.scalar(
                select(ExamQuestionTrace).where(
                    ExamQuestionTrace.attempt_id == new_attempt_id
                )
            )
            assert trace is not None
            answer_key = {
                question.id: question.correct_answer
                for question in db.scalars(
                    select(Question).where(Question.id.in_(trace.question_ids))
                ).all()
            }
            answers = {
                question_id: answer_key[question_id]
                for question_id in trace.question_ids
            }

        submit_response = client.post(
            f"/api/v1/exams/{new_attempt_id}/submit",
            headers=admin_headers,
            json={"answers": answers},
        )
        assert submit_response.status_code == 200
        submitted_attempt = submit_response.json()
        assert submitted_attempt["id"] == new_attempt_id
        assert submitted_attempt["status"] == "submitted"
        assert submitted_attempt["passed"] is True

        incidents_response = client.get(
            "/api/v1/center-incidents?status_filter=resolved",
            headers=admin_headers,
        )
        assert incidents_response.status_code == 200
        assert any(
            item["id"] == incident["id"]
            for item in incidents_response.json()["items"]
        )

        audit_response = client.get(
            "/api/v1/supervision/audit-logs?action=center_incident.resolved&limit=25",
            headers=admin_headers,
        )
        assert audit_response.status_code == 200
        assert any(
            log["entity_id"] == incident["id"]
            for log in audit_response.json()["items"]
        )
