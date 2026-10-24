"""Démarrage et soumission d'un examen officiel, gardes d'accès comprises.

Un examen ne démarre que pour un candidat dont l'identité est vérifiée, la
réservation payée, et l'entrée contrôlée au centre dans la fenêtre horaire de
la session, sur une banque homologuée dont chaque question a un média exploitable.
"""
from fastapi.testclient import TestClient

from app.main import app
from tests.conftest import get_admin_headers, prepare_checked_in_booking, seed_media_ready_official_bank


def test_exam_attempt_can_be_started_and_submitted() -> None:
    with TestClient(app) as client:
        headers = get_admin_headers(client)
        seed_media_ready_official_bank(client, headers)
        ready = prepare_checked_in_booking(client, headers)

        attempt_response = client.post("/api/v1/exams/start", headers=headers, json={
            "candidate_id": ready["candidate"]["id"], "session_id": ready["session"]["id"],
        })
        assert attempt_response.status_code == 201, attempt_response.text
        attempt = attempt_response.json()

        questions = client.get(f"/api/v1/exams/{attempt['id']}/questions", headers=headers).json()["questions"]
        assert len(questions) == 40
        submit_response = client.post(f"/api/v1/exams/{attempt['id']}/submit", headers=headers,
                                      json={"answers": {q["id"]: q["options"][0] for q in questions}})
        assert submit_response.status_code == 200, submit_response.text
        assert submit_response.json()["status"] == "submitted"


def test_exam_attempt_can_start_from_booking_reference() -> None:
    with TestClient(app) as client:
        headers = get_admin_headers(client)
        seed_media_ready_official_bank(client, headers)
        ready = prepare_checked_in_booking(client, headers)

        attempt_response = client.post("/api/v1/exams/start-from-booking", headers=headers,
                                       json={"booking_reference": ready["booking"]["reference"]})

        assert attempt_response.status_code == 201, attempt_response.text
        attempt = attempt_response.json()
        assert attempt["candidate_id"] == ready["candidate"]["id"]
        assert attempt["session_id"] == ready["session"]["id"]
        assert attempt["status"] == "started"


def test_exam_cannot_start_without_center_check_in() -> None:
    with TestClient(app) as client:
        headers = get_admin_headers(client)
        seed_media_ready_official_bank(client, headers)
        ready = prepare_checked_in_booking(client, headers, check_in=False)

        response = client.post("/api/v1/exams/start-from-booking", headers=headers,
                               json={"booking_reference": ready["booking"]["reference"]})

        assert response.status_code == 409, response.text
        assert response.json()["detail"]["code"] == "CHECKIN_REQUIRED_BEFORE_EXAM"
