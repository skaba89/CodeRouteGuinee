from datetime import UTC, datetime, timedelta
from uuid import uuid4

from fastapi.testclient import TestClient

from app.db.session import init_db
from app.main import app
from tests.conftest import seed_media_ready_official_bank, verify_candidate_identity


def _auth_headers(client: TestClient, role: str) -> dict[str, str]:
    init_db()
    suffix = uuid4().hex
    email = f"{role}-trace-e2e-{suffix}@coderoute.local"
    password = "AdminPass123!"

    register_response = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "full_name": f"{role.title()} Trace E2E",
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


def test_exam_question_trace_is_created_and_used_for_scoring() -> None:
    suffix = uuid4().hex[:8]

    with TestClient(app) as client:
        admin_headers = _auth_headers(client, "admin")
        super_headers = _auth_headers(client, "super_admin")

        # La trace officielle doit être testée sur une banque réellement
        # publiable : 40 questions approuvées avec médias candidat exploitables.
        seed_media_ready_official_bank(client, super_headers, marker=f"trace-{suffix}")

        center_response = client.post(
            "/api/v1/centers",
            headers=admin_headers,
            json={
                "code": f"CTR-QT-{suffix}",
                "name": "Centre Trace E2E",
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
                "starts_at": (datetime.now(UTC) + timedelta(days=11)).isoformat(),
                "capacity": 20,
            },
        )
        assert session_response.status_code == 201
        session = session_response.json()

        candidate_response = client.post(
            "/api/v1/candidates",
            headers=admin_headers,
            json={
                "first_name": "Ibrahima",
                "last_name": f"Trace-{suffix}",
                "identity_number": f"ID-QT-{suffix}",
                "phone": "+224629000001",
                "permit_category": "B",
            },
        )
        assert candidate_response.status_code == 201
        candidate = candidate_response.json()
        verify_candidate_identity(
            client,
            candidate["id"],
            admin_headers,
            marker=f"trace-{suffix}",
        )

        # /exams/start est désormais l'override administratif explicite.
        # Les agents centre doivent utiliser start-from-booking.
        start_response = client.post(
            "/api/v1/exams/start",
            headers=admin_headers,
            json={"candidate_id": candidate["id"], "session_id": session["id"]},
        )
        assert start_response.status_code == 201, start_response.text
        attempt = start_response.json()

        trace_response = client.get(
            f"/api/v1/exam-question-traces/attempts/{attempt['id']}",
            headers=admin_headers,
        )
        assert trace_response.status_code == 200
        trace = trace_response.json()
        assert trace["attempt_id"] == attempt["id"]
        assert trace["question_count"] == 40
        assert trace["bank_hash"]
        assert "official-" in trace["version_label"]
        assert len(trace["question_ids"]) == trace["question_count"]

        # Récupérer les bonnes réponses depuis la DB (bypass pagination API).
        from sqlalchemy import select as _select

        from app.db.session import SessionLocal as _SL
        from app.models_exam_attempt import ExamAttempt as _Attempt
        from app.models_question import Question as _Q

        _db = _SL()
        _all_q = _db.scalars(_select(_Q).where(_Q.is_active)).all()
        active_answer_key = {q.id: q.correct_answer for q in _all_q}
        _db.close()
        answers = {
            question_id: active_answer_key[question_id]
            for question_id in trace["question_ids"]
        }

        # Une soumission volontairement incomplète doit rester active et ne
        # produire ni score ni résultat final, même via un appel direct à l'API.
        missing_id = trace["question_ids"][-1]
        partial_answers = {
            question_id: answer
            for question_id, answer in answers.items()
            if question_id != missing_id
        }
        incomplete_response = client.post(
            f"/api/v1/exams/{attempt['id']}/submit",
            headers=admin_headers,
            json={"answers": partial_answers},
        )
        assert incomplete_response.status_code == 409, incomplete_response.text
        incomplete_detail = incomplete_response.json()["detail"]
        assert incomplete_detail["code"] == "EXAM_INCOMPLETE_ANSWERS"
        assert incomplete_detail["answered_questions"] == 39
        assert incomplete_detail["required_questions"] == 40
        assert incomplete_detail["missing_count"] == 1
        # Ne jamais exposer l'identifiant manquant ni une bonne réponse.
        assert "question_ids" not in incomplete_detail
        assert "correct_answer" not in incomplete_detail

        status_response = client.get(
            f"/api/v1/exams/{attempt['id']}/status",
            headers=admin_headers,
        )
        assert status_response.status_code == 200
        assert status_response.json()["status"] == "started"
        assert status_response.json()["score"] is None
        assert status_response.json()["passed"] is None

        # Simuler la dernière réponse déjà autosauvegardée par le client. La
        # façade doit fusionner la copie serveur avec le payload final au lieu
        # d'exiger que le navigateur renvoie inutilement les 40 valeurs.
        _db = _SL()
        saved_attempt = _db.get(_Attempt, attempt["id"])
        assert saved_attempt is not None
        saved_attempt.answers = {missing_id: answers[missing_id]}
        _db.add(saved_attempt)
        _db.commit()
        _db.close()

        submit_response = client.post(
            f"/api/v1/exams/{attempt['id']}/submit",
            headers=admin_headers,
            json={"answers": partial_answers},
        )
        assert submit_response.status_code == 200, submit_response.text
        submitted = submit_response.json()
        assert submitted["status"] == "submitted"
        assert submitted["score"] == trace["question_count"]
        assert submitted["passed"] is True

        audit_response = client.get(
            "/api/v1/supervision/audit-logs?action=exam.question_trace_created&limit=25",
            headers=admin_headers,
        )
        assert audit_response.status_code == 200
        logs = audit_response.json()["items"]
        assert any(log["details"]["attempt_id"] == attempt["id"] for log in logs)

        incomplete_audit_response = client.get(
            "/api/v1/supervision/audit-logs?action=exam.incomplete_submission&limit=25",
            headers=admin_headers,
        )
        assert incomplete_audit_response.status_code == 200
        incomplete_logs = incomplete_audit_response.json()["items"]
        assert any(
            log["entity_id"] == attempt["id"]
            and log["details"]["missing_count"] == 1
            and log["details"]["required_questions"] == 40
            for log in incomplete_logs
        )
