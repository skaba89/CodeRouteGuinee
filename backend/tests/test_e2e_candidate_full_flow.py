from datetime import datetime, timedelta
from app.time_utils import utc_now
from uuid import uuid4

from fastapi.testclient import TestClient

from app.db.session import init_db
from app.main import app


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
        headers = _admin_headers(client)

        center_response = client.post(
            "/api/v1/centers",
            headers=headers,
            json={
                "code": f"CTR-E2E-{suffix}",
                "name": "Centre E2E Conakry",
                "city": "Conakry",
                "address": "Kaloum",
                "capacity": 50,
                "status": "accredited",
            },
        )
        assert center_response.status_code == 201
        center = center_response.json()

        session_response = client.post(
            "/api/v1/sessions",
            headers=headers,
            json={
                "center_id": center["id"],
                "starts_at": (utc_now() + timedelta(days=7)).isoformat(),
                "capacity": 40,
            },
        )
        assert session_response.status_code == 201
        session = session_response.json()

        for index in range(40):
            question_response = client.post(
                "/api/v1/questions",
                headers=headers,
                json={
                    "category": "signalisation",
                    "text": f"Question E2E {suffix}-{index}",
                    "options": ["A", "B", "C"],
                    "correct_answer": "A",
                    "explanation": "Reponse de test E2E",
                },
            )
            assert question_response.status_code == 201

        candidate_response = client.post(
            "/api/v1/candidates",
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

        booking_response = client.post(
            "/api/v1/bookings",
            json={"candidate_id": candidate["id"], "session_id": session["id"]},
        )
        assert booking_response.status_code == 201
        booking = booking_response.json()

        convocation_response = client.get(f"/api/v1/bookings/{booking['reference']}/convocation")
        assert convocation_response.status_code == 200
        convocation = convocation_response.json()
        assert convocation["reference"] == booking["reference"]
        assert convocation["candidate"]["reference"] == candidate["reference"]
        assert convocation["qr_payload"].startswith("CODEROUTE-GN")

        qr_response = client.get(f"/api/v1/bookings/{booking['reference']}/convocation/qr.svg")
        assert qr_response.status_code == 200
        assert "image/svg+xml" in qr_response.headers["content-type"]
        assert qr_response.text.lstrip().startswith("<?xml")
        assert "<svg" in qr_response.text

        payment_response = client.post(
            "/api/v1/payments",
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

        entry_response = client.post(
            "/api/v1/entries/validate",
            json={
                "reference": booking["reference"],
                "verification_code": booking["verification_code"],
                "center_code": center["code"],
            },
        )
        assert entry_response.status_code == 200
        entry = entry_response.json()
        assert entry["allowed"] is True
        assert entry["status"] == "checked_in"

        start_response = client.post(
            "/api/v1/exams/start",
            json={"candidate_id": candidate["id"], "session_id": session["id"]},
        )
        assert start_response.status_code == 201
        attempt = start_response.json()
        assert attempt["status"] == "started"

        questions_response = client.get("/api/v1/questions")
        assert questions_response.status_code == 200
        answers = {question["id"]: question["correct_answer"] for question in questions_response.json()}
        assert len(answers) >= 40

        submit_response = client.post(
            f"/api/v1/exams/{attempt['id']}/submit",
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

        pdf_response = client.get(f"/api/v1/exams/{attempt['id']}/certificate.pdf")
        assert pdf_response.status_code == 200
        assert pdf_response.content.startswith(b"%PDF")
        assert pdf_response.headers["content-type"] == "application/pdf"
