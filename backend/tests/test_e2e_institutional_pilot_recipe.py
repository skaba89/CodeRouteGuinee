from datetime import datetime, timedelta
from uuid import uuid4

from fastapi.testclient import TestClient

from app.db.session import init_db
from app.main import app


def _admin_headers(client: TestClient) -> dict[str, str]:
    init_db()
    suffix = uuid4().hex
    email = f"admin-pilot-recipe-{suffix}@coderoute.local"
    password = "AdminPass123!"

    register_response = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "full_name": "Admin Recette Pilote",
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


def test_institutional_pilot_recipe_from_official_imports_to_certificate() -> None:
    suffix = uuid4().hex[:8].upper()
    center_code = f"PILOT-CTR-{suffix}"
    identity_number = f"GN-PILOT-ID-{suffix}"

    with TestClient(app) as client:
        headers = _admin_headers(client)

        center_payload = {
            "source": "Liste officielle DNTT - recette",
            "reason": "Simulation puis import centre pilote",
            "centers": [
                {
                    "code": center_code,
                    "name": "Centre Pilote Institutionnel",
                    "city": "Conakry",
                    "address": "Kaloum",
                    "capacity": 40,
                    "status": "accredited",
                }
            ],
        }
        center_dry_run = client.post("/api/v1/centers/import-official", headers=headers, json={**center_payload, "dry_run": True})
        assert center_dry_run.status_code == 200
        assert center_dry_run.json()["dry_run"] is True
        assert center_dry_run.json()["created"] == 1

        center_import = client.post("/api/v1/centers/import-official", headers=headers, json={**center_payload, "dry_run": False})
        assert center_import.status_code == 200
        assert center_import.json()["created"] == 1
        center = next(item for item in client.get("/api/v1/centers").json() if item["code"] == center_code)

        candidate_payload = {
            "source": "Registre national pilote - recette",
            "reason": "Simulation puis import candidat pilote",
            "candidates": [
                {
                    "first_name": "Aissatou",
                    "last_name": "Camara",
                    "identity_number": identity_number,
                    "phone": "+224620000101",
                    "permit_category": "B",
                    "status": "verified",
                }
            ],
        }
        candidate_dry_run = client.post("/api/v1/candidates/import-official", headers=headers, json={**candidate_payload, "dry_run": True})
        assert candidate_dry_run.status_code == 200
        assert candidate_dry_run.json()["dry_run"] is True
        assert candidate_dry_run.json()["created"] == 1

        candidate_import = client.post("/api/v1/candidates/import-official", headers=headers, json={**candidate_payload, "dry_run": False})
        assert candidate_import.status_code == 200
        candidate_id = candidate_import.json()["candidate_ids"][0]
        candidate_reference = candidate_import.json()["references"][0]

        question_rows = [
            {
                "category": "recette-pilote",
                "text": f"Question officielle pilote {suffix} numero {index:02d}",
                "options": ["Reponse conforme", "Reponse non conforme", "Ne sait pas"],
                "correct_answer": "Reponse conforme",
                "explanation": "Question officielle de recette pilote.",
                "is_active": True,
            }
            for index in range(40)
        ]
        question_payload = {
            "source": "Commission nationale du code - recette",
            "reason": "Chargement banque officielle pilote",
            "questions": question_rows,
        }
        question_dry_run = client.post("/api/v1/questions/import-official", headers=headers, json={**question_payload, "dry_run": True})
        assert question_dry_run.status_code == 200
        assert question_dry_run.json()["created"] == 40

        question_import = client.post("/api/v1/questions/import-official", headers=headers, json={**question_payload, "dry_run": False})
        assert question_import.status_code == 200
        assert question_import.json()["imported"] == 40

        session_response = client.post(
            "/api/v1/sessions",
            headers=headers,
            json={
                "center_id": center["id"],
                "starts_at": (datetime.utcnow() + timedelta(days=7)).isoformat(),
                "capacity": 40,
            },
        )
        assert session_response.status_code == 201
        session = session_response.json()

        booking_response = client.post("/api/v1/bookings", json={"candidate_id": candidate_id, "session_id": session["id"]})
        assert booking_response.status_code == 201
        booking = booking_response.json()

        payment_payload = {
            "source": "Orange Money - recette",
            "reason": "Rapprochement paiement pilote",
            "payments": [
                {
                    "booking_reference": booking["reference"],
                    "amount_gnf": 250000,
                    "provider": "orange_money",
                    "phone": "+224620000101",
                    "status": "paid",
                    "receipt_number": f"OM-PILOT-{suffix}",
                }
            ],
        }
        payment_dry_run = client.post("/api/v1/payments/admin/import-official", headers=headers, json={**payment_payload, "dry_run": True})
        assert payment_dry_run.status_code == 200
        assert payment_dry_run.json()["dry_run"] is True
        assert payment_dry_run.json()["created"] == 1

        payment_import = client.post("/api/v1/payments/admin/import-official", headers=headers, json={**payment_payload, "dry_run": False})
        assert payment_import.status_code == 200
        assert payment_import.json()["created"] == 1

        convocation_pdf = client.get(f"/api/v1/documents/convocations/{booking['reference']}.pdf")
        assert convocation_pdf.status_code == 200
        assert convocation_pdf.content.startswith(b"%PDF")

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
                "device_key": f"PILOT-DEVICE-{suffix}",
                "device_label": "Poste pilote recette",
            },
        )
        assert start_response.status_code == 201
        attempt = start_response.json()
        assert attempt["status"] == "started"

        questions = client.get("/api/v1/questions").json()
        imported_questions = [question for question in questions if question["category"] == "recette-pilote" and suffix in question["text"]]
        assert len(imported_questions) == 40
        answers = {question["id"]: question["correct_answer"] for question in questions}

        submit_response = client.post(f"/api/v1/exams/{attempt['id']}/submit", json={"answers": answers})
        assert submit_response.status_code == 200
        submitted_attempt = submit_response.json()
        assert submitted_attempt["passed"] is True

        certificate = client.get(f"/api/v1/exams/{attempt['id']}/certificate/verify")
        assert certificate.status_code == 200
        assert certificate.json()["candidate_reference"] == candidate_reference
        assert certificate.json()["center_name"] == center["name"]

        operations = client.get("/api/v1/operations/summary", headers=headers)
        assert operations.status_code == 200
        assert operations.json()["audit_events_24h"] > 0

        for action in [
            "candidate.official_import",
            "center.official_import",
            "question.official_import",
            "payments.official_import",
        ]:
            audit_response = client.get(f"/api/v1/supervision/audit-logs?action={action}&limit=25", headers=headers)
            assert audit_response.status_code == 200
            assert any(log["action"] == action for log in audit_response.json())
