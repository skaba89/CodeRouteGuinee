"""Lien d'attestation envoyé avec le résultat : page publique configurable.

Régression : le lien était codé en dur vers https://api.coderoute.gov.gn, quel
que soit l'environnement, et pointait vers l'API JSON au lieu de la page de
vérification utilisée par le QR de l'attestation.
"""
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.main import app
from app.models_candidate import Candidate
from app.models_question import Question
from tests.conftest import get_admin_headers, prepare_checked_in_booking, seed_media_ready_official_bank


def test_passing_result_email_links_to_public_verification_page() -> None:
    with TestClient(app) as client:
        headers = get_admin_headers(client)
        seed_media_ready_official_bank(client, headers)
        ready = prepare_checked_in_booking(client, headers)
        with SessionLocal() as db:
            candidate = db.get(Candidate, ready["candidate"]["id"])
            candidate.email = "resultat.attestation@example.org"
            db.commit()

        attempt = client.post("/api/v1/exams/start", headers=headers, json={
            "candidate_id": ready["candidate"]["id"], "session_id": ready["session"]["id"],
        }).json()
        questions = client.get(f"/api/v1/exams/{attempt['id']}/questions", headers=headers).json()["questions"]
        with SessionLocal() as db:
            answers = {q["id"]: db.get(Question, q["id"]).correct_answer for q in questions}

        with patch("app.email_service.send_exam_result") as send:
            response = client.post(f"/api/v1/exams/{attempt['id']}/submit", headers=headers,
                                   json={"answers": answers})

    assert response.status_code == 200, response.text
    assert response.json()["passed"] is True
    send.assert_called_once()
    expected = f"{get_settings().public_app_url.rstrip('/')}/#/verifier/{attempt['id']}"
    assert send.call_args.kwargs["certificate_url"] == expected
