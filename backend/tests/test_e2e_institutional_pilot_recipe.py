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
        authority_headers = get_admin_headers(client)

        center_payload = {
            "source": "Liste officielle DNTT - recette",
            "reason": "Simulation puis import centre pilote",
            "centers": [
                {
                    "code": center_code,
                    "name": "Centre Pilote Institutionnel",
                    "city": "Conakry",
                    "address": "Kaloum",
                    "capacity": 35,
                    "status": "accredited",
                }
            ],
        }
        center_dry_run = client.post(
            "/api/v1/centers/import-official",
            headers=headers,
            json={**center_payload, "dry_run": True},
        )
        assert center_dry_run.status_code == 200
        assert center_dry_run.json()["dry_run"] is True
        assert center_dry_run.json()["created"] == 1

        center_import = client.post(
            "/api/v1/centers/import-official",
            headers=headers,
            json={**center_payload, "dry_run": False},
        )
        assert center_import.status_code == 200
        assert center_import.json()["created"] == 1

        from sqlalchemy import select as _sel
        from app.db.session import SessionLocal as _SL
        from app.models_center import Center as _Ctr

        with _SL() as _db:
            imported_center = _db.scalar(_sel(_Ctr).where(_Ctr.code == center_code))
            assert imported_center is not None, f"Centre {center_code} non trouvé"
            center = {
                "id": imported_center.id,
                "code": imported_center.code,
                "capacity": imported_center.capacity,
                "name": imported_center.name,
            }

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
        candidate_dry_run = client.post(
            "/api/v1/candidates/import-official",
            headers=headers,
            json={**candidate_payload, "dry_run": True},
        )
        assert candidate_dry_run.status_code == 200
        assert candidate_dry_run.json()["dry_run"] is True
        assert candidate_dry_run.json()["created"] == 1

        candidate_import = client.post(
            "/api/v1/candidates/import-official",
            headers=headers,
            json={**candidate_payload, "dry_run": False},
        )
        assert candidate_import.status_code == 200
        candidate_id = candidate_import.json()["candidate_ids"][0]
        candidate_reference = candidate_import.json()["references"][0]

        # L'import officiel doit produire une banque qui respecte réellement la
        # distribution nationale et le gate média candidat, pas 40 questions
        # d'une catégorie artificielle sans illustration.
        question_rows = [
            {
                "category": row["category"],
                "text": f"{row['text']} [PILOT-{suffix}-{index:02d}]",
                "options": row["options"],
                "correct_answer": row["correct_answer"],
                "explanation": row.get("explanation") or "Question officielle de recette pilote.",
                "media_type": "image",
                "media_url": f"https://cdn.example.com/coderoute-pilot/{suffix}/{index}.webp",
                "media_alt": f"Illustration officielle pilote {index + 1}",
                "is_active": True,
            }
            for index, row in enumerate(QUESTIONS_GN)
        ]
        assert len(question_rows) == 40
        question_payload = {
            "source": "Commission nationale du code - recette",
            "reason": "Chargement banque officielle pilote",
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

        # L'import établit la provenance ; l'approbation DNTT reste une décision
        # séparée et explicite de super-admin.
        for question_id in imported["question_ids"]:
            approval = client.post(
                f"/api/v1/questions/{question_id}/approve",
                headers=authority_headers,
            )
            assert approval.status_code == 200, approval.text

        # Le check-in et le démarrage officiels sont volontairement testés dans
        # leur fenêtre opérationnelle réelle.
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
        payment_dry_run = client.post(
            "/api/v1/payments/admin/import-official",
            headers=headers,
            json={**payment_payload, "dry_run": True},
        )
        assert payment_dry_run.status_code == 200
        assert payment_dry_run.json()["dry_run"] is True
        assert payment_dry_run.json()["created"] == 1

        payment_import = client.post(
            "/api/v1/payments/admin/import-official",
            headers=headers,
            json={**payment_payload, "dry_run": False},
        )
        assert payment_import.status_code == 200
        assert payment_import.json()["created"] == 1

        convocation_pdf = client.get(
            f"/api/v1/documents/convocations/{booking['reference']}.pdf",
            headers=headers,
        )
        assert convocation_pdf.status_code == 200
        assert convocation_pdf.content.startswith(b"%PDF")

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
        assert entry_response.json()["allowed"] is True, entry_response.text

        start_response = client.post(
            "/api/v1/exams/start-from-booking",
            headers=headers,
            json={
                "booking_reference": booking["reference"],
                "device_key": f"PILOT-DEVICE-{suffix}",
                "device_label": "Poste pilote recette",
            },
        )
        assert start_response.status_code == 201, start_response.text
        attempt = start_response.json()
        assert attempt["status"] == "started"

        from app.models_exam_question_trace import ExamQuestionTrace as _Trace
        from app.models_question import Question as _Question

        with _SL() as db:
            trace = db.scalar(_sel(_Trace).where(_Trace.attempt_id == attempt["id"]))
            assert trace is not None
            selected_questions = db.scalars(
                _sel(_Question).where(_Question.id.in_(trace.question_ids))
            ).all()
            answers = {question.id: question.correct_answer for question in selected_questions}

        assert len(answers) == 40
        submit_response = client.post(
            f"/api/v1/exams/{attempt['id']}/submit",
            headers=headers,
            json={"answers": answers},
        )
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
            audit_response = client.get(
                f"/api/v1/supervision/audit-logs?action={action}&limit=25",
                headers=headers,
            )
            assert audit_response.status_code == 200
            assert any(log["action"] == action for log in audit_response.json()["items"])
