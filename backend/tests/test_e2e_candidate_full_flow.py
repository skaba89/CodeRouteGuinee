from datetime import UTC, datetime, timedelta
from uuid import uuid4

from fastapi.testclient import TestClient

from app.db.session import init_db
from app.main import app
from tests.conftest import (
    get_admin_headers,
    seed_media_ready_official_bank,
    verify_candidate_identity,
)


def _admin_headers(client: TestClient) -> dict[str, str]:
    init_db()
    suffix = uuid4().hex
    email = f"admin-candidate-e2e-{suffix}@coderoute.local"
    password = "AdminPass123!"

    register_response = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "full_name": "Admin Candidate E2E",
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
    token = login_response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_candidate_booking_payment_entry_exam_certificate_flow() -> None:
    suffix = uuid4().hex[:8]

    with TestClient(app) as client:
        # L'autorité super-admin sert uniquement à homologuer la banque média.
        super_headers = get_admin_headers(client)
        headers = _admin_headers(client)
        seed_media_ready_official_bank(client, super_headers, marker=f"full-{suffix}")

        center_response = client.post(
            "/api/v1/centers",
            headers=headers,
            json={
                "code": f"CTR-E2E-{suffix}",
                "name": "Centre E2E Conakry",
                "city": "Conakry",
                "address": "Kaloum",
                "capacity": 35,
                "status": "accredited",
            },
        )
        assert center_response.status_code == 201
        center = center_response.json()

        # Le parcours standard doit être dans la fenêtre opérationnelle de
        # check-in et de démarrage, pas à J+7 comme l'ancien scénario.
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

        candidate_response = client.post(
            "/api/v1/candidates",
            headers=headers,
            json={
                "first_name": "Mamadou",
                "last_name": "Diallo",
                "identity_number": f"ID-E2E-{suffix}",
                "phone": "+224622000010",
                "permit_category": "B",
            },
        )
        assert candidate_response.status_code == 201
        candidate = candidate_response.json()

        # L'état verified ne peut plus être forcé via PATCH : on passe par la
        # décision d'identité officielle, comme en production.
        verify_candidate_identity(
            client,
            candidate["id"],
            headers,
            marker=f"full-{suffix}",
        )

        booking_response = client.post(
            "/api/v1/bookings",
            headers=headers,
            json={"candidate_id": candidate["id"], "session_id": session["id"]},
        )
        assert booking_response.status_code == 201
        booking = booking_response.json()

        convocation_response = client.get(
            f"/api/v1/bookings/{booking['reference']}/convocation",
            headers=headers,
        )
        assert convocation_response.status_code == 200
        convocation = convocation_response.json()
        assert convocation["reference"] == booking["reference"]
        assert convocation["candidate"]["reference"] == candidate["reference"]
        assert convocation["qr_payload"].startswith("CODEROUTE-GN")

        qr_response = client.get(
            f"/api/v1/bookings/{booking['reference']}/convocation/qr.svg",
            headers=headers,
        )
        assert qr_response.status_code == 200
        assert "image/svg+xml" in qr_response.headers["content-type"]
        assert qr_response.text.lstrip().startswith("<?xml")
        assert "<svg" in qr_response.text

        payment_response = client.post(
            "/api/v1/payments",
            headers=headers,
            json={
                "booking_reference": booking["reference"],
                "amount_gnf": 250000,
                "provider": "sandbox",
                "phone": "+224622000010",
            },
        )
        assert payment_response.status_code == 201
        payment = payment_response.json()
        assert payment["booking_reference"] == booking["reference"]
        assert payment["status"] == "paid"

        # Le test porte sur le parcours citoyen bout-en-bout, pas sur le
        # cloisonnement d'un compte agent centre (couvert séparément).
        entry_response = client.post(
            "/api/v1/entries/validate",
            headers=headers,
            json={
                "reference": booking["reference"],
                "verification_code": booking["verification_code"],
                "center_code": center["code"],
            },
        )
        assert entry_response.status_code == 200, entry_response.text
        entry = entry_response.json()
        assert entry["allowed"] is True
        assert entry["status"] == "checked_in"

        start_response = client.post(
            "/api/v1/exams/start-from-booking",
            headers=headers,
            json={"booking_reference": booking["reference"]},
        )
        assert start_response.status_code == 201, start_response.text
        attempt = start_response.json()
        assert attempt["status"] == "started"

        # Récupérer les bonnes réponses depuis la trace officielle plutôt que
        # supposer que toutes les questions actives appartiennent à la tentative.
        from sqlalchemy import select as _select

        from app.db.session import SessionLocal as _SL
        from app.models_exam_question_trace import ExamQuestionTrace as _Trace
        from app.models_question import Question as _Q

        _db = _SL()
        trace = _db.scalar(
            _select(_Trace).where(_Trace.attempt_id == attempt["id"])
        )
        assert trace is not None
        answer_key = {
            question.id: question.correct_answer
            for question in _db.scalars(
                _select(_Q).where(_Q.id.in_(trace.question_ids))
            ).all()
        }
        _db.close()
        answers = {question_id: answer_key[question_id] for question_id in trace.question_ids}
        assert len(answers) == 40

        submit_response = client.post(
            f"/api/v1/exams/{attempt['id']}/submit",
            headers=headers,
            json={"answers": answers},
        )
        assert submit_response.status_code == 200
        submitted_attempt = submit_response.json()
        assert submitted_attempt["status"] == "submitted"
        assert submitted_attempt["passed"] is True

        certificate_response = client.get(f"/api/v1/exams/{attempt['id']}/certificate/verify")
        assert certificate_response.status_code == 200
        certificate = certificate_response.json()
        assert certificate["valid"] is True
        assert certificate["candidate_reference"] == candidate["reference"]
        assert certificate["center_name"] == center["name"]

        pdf_response = client.get(
            f"/api/v1/exams/{attempt['id']}/certificate.pdf",
            headers=headers,
        )
        assert pdf_response.status_code == 200
        assert pdf_response.content.startswith(b"%PDF")
        assert pdf_response.headers["content-type"] == "application/pdf"
