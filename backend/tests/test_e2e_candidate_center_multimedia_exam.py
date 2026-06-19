from datetime import datetime, timedelta
from app.time_utils import utc_now
from uuid import uuid4

from fastapi.testclient import TestClient

from app.db.session import init_db
from app.main import app


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
    rows = []
    for index in range(40):
        is_video = index % 2 == 1
        media_type = "video" if is_video else "image"
        media_url = (
            f"https://cdn.coderoute.gov.gn/exam/videos/{suffix.lower()}-{index:02d}.mp4"
            if is_video
            else f"https://cdn.coderoute.gov.gn/exam/images/{suffix.lower()}-{index:02d}.jpg"
        )
        rows.append(
            {
                "category": "multimedia-pilote",
                "text": f"Scenario multimedia officiel {suffix} numero {index:02d}",
                "options": ["Action securisee", "Action dangereuse", "Aucune action", "Klaxonner"],
                "correct_answer": "Action securisee",
                "explanation": "La reponse attendue respecte la conduite preventive.",
                "media_type": media_type,
                "media_url": media_url,
                "media_alt": f"Illustration {media_type} du scenario {index:02d}",
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

        center_payload = {
            "source": "DNTT - centres multimedia pilotes",
            "reason": "Inscription centre pilote multimedia",
            "centers": [
                {
                    "code": center_code,
                    "name": "Centre Multimedia Pilote",
                    "city": "Conakry",
                    "address": "Route Le Prince",
                    "capacity": 40,
                    "status": "accredited",
                }
            ],
        }
        assert client.post("/api/v1/centers/import-official", headers=headers, json={**center_payload, "dry_run": True}).json()["created"] == 1
        center_import = client.post("/api/v1/centers/import-official", headers=headers, json={**center_payload, "dry_run": False})
        assert center_import.status_code == 200
        center = next(item for item in client.get("/api/v1/centers").json() if item["code"] == center_code)

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
        candidate_dry_run = client.post("/api/v1/candidates/import-official", headers=headers, json={**candidate_payload, "dry_run": True})
        assert candidate_dry_run.status_code == 200
        assert candidate_dry_run.json()["created"] == 1
        candidate_import = client.post("/api/v1/candidates/import-official", headers=headers, json={**candidate_payload, "dry_run": False})
        assert candidate_import.status_code == 200
        candidate_id = candidate_import.json()["candidate_ids"][0]
        candidate_reference = candidate_import.json()["references"][0]

        question_rows = _multimedia_questions(suffix)
        question_payload = {
            "source": "Banque multimedia nationale pilote",
            "reason": "Chargement de 40 questions illustrees",
            "questions": question_rows,
        }
        question_dry_run = client.post("/api/v1/questions/import-official", headers=headers, json={**question_payload, "dry_run": True})
        assert question_dry_run.status_code == 200
        assert question_dry_run.json()["created"] == 40
        question_import = client.post("/api/v1/questions/import-official", headers=headers, json={**question_payload, "dry_run": False})
        assert question_import.status_code == 200
        assert question_import.json()["imported"] == 40

        fetched_questions = client.get("/api/v1/questions").json()
        imported_questions = [question for question in fetched_questions if question["category"] == "multimedia-pilote" and suffix in question["text"]]
        assert len(imported_questions) == 40
        assert sum(1 for question in imported_questions if question["media_type"] == "image") == 20
        assert sum(1 for question in imported_questions if question["media_type"] == "video") == 20
        assert all(question["media_url"] and question["media_alt"] for question in imported_questions)

        session_response = client.post(
            "/api/v1/sessions",
            headers=headers,
            json={
                "center_id": center["id"],
                "starts_at": (utc_now() + timedelta(days=10)).isoformat(),
                "capacity": 40,
            },
        )
        assert session_response.status_code == 201
        session = session_response.json()

        booking_response = client.post("/api/v1/bookings", json={"candidate_id": candidate_id, "session_id": session["id"]})
        assert booking_response.status_code == 201
        booking = booking_response.json()

        convocation_response = client.get(f"/api/v1/bookings/{booking['reference']}/convocation")
        assert convocation_response.status_code == 200
        assert convocation_response.json()["candidate"]["reference"] == candidate_reference

        entry_response = client.post(
            "/api/v1/entries/validate",
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
            json={
                "booking_reference": booking["reference"],
                "device_key": f"MM-DEVICE-{suffix}",
                "device_label": "Poste multimedia 01",
            },
        )
        assert start_response.status_code == 201
        attempt = start_response.json()

        answers = {question["id"]: question["correct_answer"] for question in fetched_questions}
        submit_response = client.post(f"/api/v1/exams/{attempt['id']}/submit", json={"answers": answers})
        assert submit_response.status_code == 200
        submitted_attempt = submit_response.json()
        assert submitted_attempt["status"] == "submitted"
        assert submitted_attempt["passed"] is True
        assert submitted_attempt["score"] >= 40

        certificate = client.get(f"/api/v1/exams/{attempt['id']}/certificate/verify")
        assert certificate.status_code == 200
        assert certificate.json()["valid"] is True
        assert certificate.json()["candidate_reference"] == candidate_reference
        assert certificate.json()["center_name"] == center["name"]

        exam_summary = client.get("/api/v1/exams/summary")
        assert exam_summary.status_code == 200
        assert exam_summary.json()["submitted_attempts"] >= 1

        audit_response = client.get("/api/v1/supervision/audit-logs?action=exam.question_trace_created&limit=25", headers=headers)
        assert audit_response.status_code == 200
        assert any(log["details"]["attempt_id"] == attempt["id"] and log["details"]["question_count"] >= 40 for log in audit_response.json())
