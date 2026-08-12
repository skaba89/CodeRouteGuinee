from datetime import UTC, datetime, timedelta
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db.session import SessionLocal
from app.main import app
from app.models_exam_question_trace import ExamQuestionTrace
from app.models_question import Question
from tests.conftest import get_admin_headers, seed_media_ready_official_bank, verify_candidate_identity


def test_exam_scoring_certificate_and_public_verification_end_to_end() -> None:
    suffix = uuid4().hex[:8]

    with TestClient(app) as client:
        authority_headers = get_admin_headers(client)
        seed_media_ready_official_bank(client, authority_headers, marker=f"certificate-{suffix}")

        center_response = client.post(
            "/api/v1/centers",
            headers=authority_headers,
            json={
                "code": f"CTR-EXAM-{suffix}",
                "name": "Centre Examen E2E",
                "city": "Conakry",
                "address": "Corniche",
                "capacity": 20,
                "status": "accredited",
            },
        )
        assert center_response.status_code == 201
        center = center_response.json()

        session_response = client.post(
            "/api/v1/sessions",
            headers=authority_headers,
            json={
                "center_id": center["id"],
                "starts_at": (datetime.now(UTC) + timedelta(days=7)).isoformat(),
                "capacity": 20,
            },
        )
        assert session_response.status_code == 201
        session = session_response.json()

        candidate_response = client.post(
            "/api/v1/candidates",
            headers=authority_headers,
            json={
                "first_name": "Aissatou",
                "last_name": f"Exam-{suffix}",
                "identity_number": f"ID-EXAM-{suffix}",
                "phone": "+224623000000",
                "permit_category": "B",
            },
        )
        assert candidate_response.status_code == 201
        candidate = candidate_response.json()
        verify_candidate_identity(
            client,
            candidate["id"],
            authority_headers,
            marker=f"certificate-{suffix}",
        )

        start_response = client.post(
            "/api/v1/exams/start",
            headers=authority_headers,
            json={"candidate_id": candidate["id"], "session_id": session["id"]},
        )
        assert start_response.status_code == 201, start_response.text
        attempt = start_response.json()
        assert attempt["status"] == "started"

        q_response = client.get(
            f"/api/v1/exams/{attempt['id']}/questions",
            headers=authority_headers,
        )
        assert q_response.status_code == 200
        assert len(q_response.json()["questions"]) == 40

        with SessionLocal() as db:
            trace = db.scalar(
                select(ExamQuestionTrace).where(ExamQuestionTrace.attempt_id == attempt["id"])
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

        assert len(answers) == 40
        submit_response = client.post(
            f"/api/v1/exams/{attempt['id']}/submit",
            headers=authority_headers,
            json={"answers": answers},
        )
        assert submit_response.status_code == 200
        submitted_attempt = submit_response.json()
        assert submitted_attempt["status"] == "submitted"
        assert submitted_attempt["score"] == 40
        assert submitted_attempt["passed"] is True

        duplicate_submit_response = client.post(
            f"/api/v1/exams/{attempt['id']}/submit",
            headers=authority_headers,
            json={"answers": answers},
        )
        assert duplicate_submit_response.status_code == 409

        certificate_response = client.get(
            f"/api/v1/exams/{attempt['id']}/certificate.pdf",
            headers=authority_headers,
        )
        assert certificate_response.status_code == 200
        assert certificate_response.content.startswith(b"%PDF")

        verification_response = client.get(f"/api/v1/exams/{attempt['id']}/certificate/verify")
        assert verification_response.status_code == 200
        verification = verification_response.json()
        assert verification["valid"] is True
        assert verification["attempt_id"] == attempt["id"]
        assert verification["passed"] is True
        assert verification["score"] == 40

        summary_response = client.get("/api/v1/exams/summary", headers=authority_headers)
        assert summary_response.status_code == 200
        summary = summary_response.json()
        assert summary["submitted_attempts"] >= 1
        assert summary["passed_attempts"] >= 1
