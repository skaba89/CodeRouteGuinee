from datetime import UTC, datetime, timedelta
from uuid import uuid4

from fastapi.testclient import TestClient

from app.db.session import init_db
from app.main import app
from app.question_bank_gn import QUESTIONS_GN
from tests.conftest import get_admin_headers


def _admin_headers(client: TestClient) -> dict[str, str]:
    init_db()
    suffix = uuid4().hex
    email = f"admin-multimedia-recipe-{suffix}@coderoute.local"
    password = "AdminPass123!"

    register_response = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "full_name": "Admin Recette Multimedia",
            "password": password,
            "role": "admin",
        },
    )
    assert register_response.status_code == 201

    login_response = client.post(
        "/api/v1/auth/login",
        data={"username": email, "password": password},
    )
    assert login_response.status_code == 200
    return {"Authorization": f"Bearer {login_response.json()['access_token']}"}


def _multimedia_questions(suffix: str) -> list[dict]:
    rows: list[dict] = []
    for index, official in enumerate(QUESTIONS_GN):
        is_video = index % 2 == 1
        media_type = "video" if is_video else "image"
        media_url = (
            f"https://cdn.coderoute.gov.gn/exam/videos/{suffix.lower()}-{index:02d}.mp4"
            if is_video
            else f"https://cdn.coderoute.gov.gn/exam/images/{suffix.lower()}-{index:02d}.jpg"
        )
        rows.append(
            {
                "category": official["category"],
                "text": f"{official['text']} [MM-{suffix}-{index:02d}]",
                "options": official["options"],
                "correct_answer": official["correct_answer"],
                "explanation": official.get("explanation") or "La réponse respecte la conduite préventive.",
                "media_type": media_type,
                "media_url": media_url,
                "media_alt": f"Illustration {media_type} du scénario officiel {index:02d}",
                "is_active": True,
            }
        )
    return rows


def test_candidate_registration_center_booking_and_40_question_multimedia_exam_tracking() -> None:
    suffix = uuid4().hex[:8].upper()
    center_code = f"MM-CTR-{suffix}"
    identity_number = f"GN-MM-ID-{suffix}"

    with TestClient(app) as client:
        headers = _admin_headers(client)
        authority_headers = get_admin_headers(client)

        center_payload = {
            "source": "DNTT - centres multimedia pilotes",
            "reason": "Inscription centre pilote multimedia",
            "centers": [
                {
                    "code": center_code,
                    "name": "Centre Multimedia Pilote",
                    "city": "Conakry",
                    "address": "Route Le Prince",
                    "capacity": 35,
                    "status": "accredited",
                }
            ],
        }
        dry_center = client.post(
            "/api/v1/centers/import-official",
            headers=headers,
            json={**center_payload, "dry_run": True},
        )
        assert dry_center.status_code == 200
        assert dry_center.json()["created"] == 1
        center_import = client.post(
            "/api/v1/centers/import-official",
            headers=headers,
            json={**center_payload, "dry_run": False},
        )
        assert center_import.status_code == 200

        from sqlalchemy import select as _sel
        from app.db.session import SessionLocal as _SL
        from app.models_center import Center as _Center

        with _SL() as db:
            imported_center = db.scalar(_sel(_Center).where(_Center.code == center_code))
            assert imported_center is not None, f"Centre {center_code} non trouvé en base"
            center = {
                "id": imported_center.id,
                "code": imported_center.code,
                "name": imported_center.name,
                "capacity": imported_center.capacity,
            }

        candidate_payload = {
            "source": "Registre candidats multimedia",
            "reason": "Inscription candidat dans centre multimedia",
            "candidates": [
                {
                    "first_name": "Moussa",
                    "last_name": "Bah",
                    "identity_number": identity_number,
                    "phone": "+224621000202",
                    "permit_category": "B",
                    "status": "verified",
                }
            ],
        }
        candidate_dry_run = client.post(
            "/api/v1/candidates/import-official",
            headers=headers,
            json={**candidate_payload, "dry_run": True},
        )
        assert candidate_dry_run.status_code == 200
        assert candidate_dry_run.json()["created"] == 1
        candidate_import = client.post(
            "/api/v1/candidates/import-official",
            headers=headers,
            json={**candidate_payload, "dry_run": False},
        )
        assert candidate_import.status_code == 200
        candidate_id = candidate_import.json()["candidate_ids"][0]
        candidate_reference = candidate_import.json()["references"][0]

        question_rows = _multimedia_questions(suffix)
        assert len(question_rows) == 40
        question_payload = {
            "source": "Banque multimedia nationale pilote",
            "reason": "Chargement de 40 questions illustrees",
            "questions": question_rows,
        }
        question_dry_run = client.post(
            "/api/v1/questions/import-official",
            headers=headers,
            json={**question_payload, "dry_run": True},
        )
        assert question_dry_run.status_code == 200
        assert question_dry_run.json()["created"] == 40
        question_import = client.post(
            "/api/v1/questions/import-official",
            headers=headers,
            json={**question_payload, "dry_run": False},
        )
        assert question_import.status_code == 200, question_import.text
        imported = question_import.json()
        assert imported["imported"] == 40
        assert len(imported["question_ids"]) == 40

        # L'import conserve sa provenance ; l'autorité DNTT approuve ensuite
        # explicitement les 40 questions avant qu'elles deviennent examinables.
        for question_id in imported["question_ids"]:
            approval = client.post(
                f"/api/v1/questions/{question_id}/approve",
                headers=authority_headers,
            )
            assert approval.status_code == 200, approval.text

        fetched_questions = client.get(
            "/api/v1/questions",
            headers=headers,
            params={"limit": 200},
        ).json()["items"]
        imported_questions = [question for question in fetched_questions if f"MM-{suffix}-" in question["text"]]
        assert len(imported_questions) == 40
        assert sum(1 for question in imported_questions if question["media_type"] == "image") == 20
        assert sum(1 for question in imported_questions if question["media_type"] == "video") == 20
        assert all(question["media_url"] and question["media_alt"] for question in imported_questions)
        assert all(question["validation_status"] == "approved" for question in imported_questions)

        from app.models_question import Question as _Question
        with _SL() as db:
            approved_rows = db.scalars(
                _sel(_Question).where(_Question.id.in_(imported["question_ids"]))
            ).all()
            answer_key = {question.id: question.correct_answer for question in approved_rows}

        session_response = client.post(
            "/api/v1/sessions",
            headers=headers,
            json={
                "center_id": center["id"],
                "starts_at": (datetime.now(UTC) + timedelta(minutes=5)).isoformat(),
                "capacity": 35,
            },
        )
        assert session_response.status_code == 201
        session = session_response.json()

        booking_response = client.post(
            "/api/v1/bookings",
            headers=headers,
            json={"candidate_id": candidate_id, "session_id": session["id"]},
        )
        assert booking_response.status_code == 201
        booking = booking_response.json()

        convocation_response = client.get(
            f"/api/v1/bookings/{booking['reference']}/convocation",
            headers=headers,
        )
        assert convocation_response.status_code == 200
        assert convocation_response.json()["candidate"]["reference"] == candidate_reference

        payment_response = client.post(
            "/api/v1/payments",
            headers=headers,
            json={
                "booking_reference": booking["reference"],
                "amount_gnf": 250000,
                "provider": "sandbox",
                "phone": "+224621000202",
            },
        )
        assert payment_response.status_code == 201
        assert payment_response.json()["status"] == "paid"

        entry_response = client.post(
            "/api/v1/entries/validate",
            headers=headers,
            json={
                "reference": booking["reference"],
                "verification_code": booking["verification_code"],
                "center_code": center_code,
            },
        )
        assert entry_response.status_code == 200
        assert entry_response.json()["allowed"] is True

        start_response = client.post(
            "/api/v1/exams/start-from-booking",
            headers=headers,
            json={
                "booking_reference": booking["reference"],
                "device_key": f"MM-DEVICE-{suffix}",
                "device_label": "Poste multimedia 01",
            },
        )
        assert start_response.status_code == 201, start_response.text
        attempt = start_response.json()

        q_resp = client.get(
            f"/api/v1/exams/{attempt['id']}/questions",
            headers=headers,
        )
        assert q_resp.status_code == 200
        exam_qs = q_resp.json()["questions"]
        assert len(exam_qs) == 40
        assert sum(1 for question in exam_qs if question["media_type"] == "image") == 20
        assert sum(1 for question in exam_qs if question["media_type"] == "video") == 20

        answers = {question["id"]: answer_key[question["id"]] for question in exam_qs}
        submit_response = client.post(
            f"/api/v1/exams/{attempt['id']}/submit",
            headers=headers,
            json={"answers": answers},
        )
        assert submit_response.status_code == 200
        submitted_attempt = submit_response.json()
        assert submitted_attempt["status"] == "submitted"
        assert submitted_attempt["passed"] is True
        assert submitted_attempt["score"] == 40

        certificate = client.get(f"/api/v1/exams/{attempt['id']}/certificate/verify")
        assert certificate.status_code == 200
        assert certificate.json()["valid"] is True
        assert certificate.json()["candidate_reference"] == candidate_reference
        assert certificate.json()["center_name"] == center["name"]

        exam_summary = client.get("/api/v1/exams/summary", headers=headers)
        assert exam_summary.status_code == 200
        assert exam_summary.json()["submitted_attempts"] >= 1

        audit_response = client.get(
            "/api/v1/supervision/audit-logs?action=exam.question_trace_created&limit=25",
            headers=headers,
        )
        assert audit_response.status_code == 200
        assert any(
            log["details"]["attempt_id"] == attempt["id"]
            and log["details"]["question_count"] == 40
            for log in audit_response.json()["items"]
        )
