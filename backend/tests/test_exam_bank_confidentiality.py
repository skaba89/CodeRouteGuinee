"""Confidentialité de la banque officielle (bonnes pratiques des examens nationaux).

Comme pour l'épreuve théorique en France, le candidat reçoit son score et ses
fautes par thème, jamais les bonnes réponses de l'examen officiel ; la banque
officielle n'est exposée ni par l'entraînement ni aux agents de centre.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from fastapi.testclient import TestClient

from app.db.session import init_db
from app.main import app
from app.question_bank_gn import QUESTIONS_GN, QUESTIONS_TRAINING_FULL
from tests.conftest import (
    get_admin_headers,
    get_auth_headers,
    get_center_agent_headers,
    seed_media_ready_official_bank,
    verify_candidate_identity,
)


def _submitted_exam_for_registered_candidate(client: TestClient) -> dict:
    """Candidat inscrit en ligne qui compose et soumet son examen officiel."""
    admin = get_admin_headers(client)
    seed_media_ready_official_bank(client, admin)
    suffix = uuid4().hex[:8]
    center = client.post("/api/v1/centers", headers=admin, json={
        "code": f"CTR-CONF-{suffix}", "name": "Centre confidentialité", "city": "Conakry",
        "address": "Kaloum", "capacity": 20, "status": "active",
    }).json()
    session = client.post("/api/v1/sessions", headers=admin, json={
        "center_id": center["id"], "capacity": 20,
        "starts_at": (datetime.now(UTC) + timedelta(minutes=5)).isoformat(),
    }).json()
    reg = client.post("/api/v1/registration/candidate", json={
        "first_name": "Kadiatou", "last_name": f"Sylla{suffix}", "email": f"conf-{suffix}@test.gn",
        "password": "MotDePasse123!", "phone": f"+224622{suffix[:6]}", "identity_number": f"NNI-CONF-{suffix}",
        "permit_category": "B",
    }).json()
    candidate = {"Authorization": f"Bearer {reg['access_token']}"}
    verify_candidate_identity(client, reg["candidate_id"], admin, marker=suffix)
    booking = client.post("/api/v1/bookings/self", headers=candidate, json={"session_id": session["id"]}).json()
    client.post("/api/v1/payments", headers=candidate, json={
        "booking_reference": booking["reference"], "amount_gnf": 150000,
        "provider": "orange_money", "phone": "+224622000111",
    })
    entry = client.post("/api/v1/entries/validate", headers=admin, json={
        "reference": booking["reference"], "verification_code": booking["verification_code"],
        "center_code": center["code"],
    })
    assert entry.json()["allowed"] is True, entry.text
    attempt = client.post("/api/v1/exams/start-from-booking", headers=candidate,
                          json={"booking_reference": booking["reference"]}).json()
    questions = client.get(f"/api/v1/exams/{attempt['id']}/questions", headers=candidate).json()["questions"]
    submit = client.post(f"/api/v1/exams/{attempt['id']}/submit", headers=candidate,
                         json={"answers": {q["id"]: q["options"][0] for q in questions}})
    assert submit.status_code == 200, submit.text
    return {"attempt": attempt, "candidate": candidate, "admin": admin, "center": center}


def test_candidate_gets_score_and_errors_by_theme_without_answers() -> None:
    init_db()
    with TestClient(app) as client:
        ctx = _submitted_exam_for_registered_candidate(client)
        response = client.get(f"/api/v1/exams/{ctx['attempt']['id']}/results", headers=ctx["candidate"])

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["detail_level"] == "summary"
    assert body["questions"] == []
    assert "correct_answer" not in response.text
    themes = body["themes"]
    assert {t["category"] for t in themes} <= {
        "signalisation", "priorites", "vitesse", "depassement",
        "securite_passive", "urgence", "alcool_drogues", "premiers_secours",
    }
    assert sum(t["total"] for t in themes) == body["total"] == 40
    assert sum(t["errors"] for t in themes) == body["total"] - body["score"]
    assert all(t["label"] for t in themes)


def test_center_agent_does_not_see_official_answers() -> None:
    init_db()
    with TestClient(app) as client:
        ctx = _submitted_exam_for_registered_candidate(client)
        agent = get_center_agent_headers(client, ctx["center"]["id"])
        response = client.get(f"/api/v1/exams/{ctx['attempt']['id']}/results", headers=agent)
    assert response.status_code == 200, response.text
    assert response.json()["detail_level"] == "summary"
    assert response.json()["questions"] == []


def test_administration_keeps_full_correction_for_appeals() -> None:
    init_db()
    with TestClient(app) as client:
        ctx = _submitted_exam_for_registered_candidate(client)
        response = client.get(f"/api/v1/exams/{ctx['attempt']['id']}/results", headers=ctx["admin"])
    body = response.json()
    assert body["detail_level"] == "full"
    assert len(body["questions"]) == 40
    assert all("correct_answer" in q for q in body["questions"])


def test_question_bank_listing_is_refused_to_center_agents() -> None:
    init_db()
    with TestClient(app) as client:
        response = client.get("/api/v1/questions", headers=get_auth_headers(client, "center"))
    assert response.status_code == 403


def test_training_never_serves_official_questions() -> None:
    official = {q["text"] for q in QUESTIONS_GN}
    init_db()
    with TestClient(app) as client:
        headers = get_auth_headers(client, "candidate")
        categories = client.get("/api/v1/training/categories", headers=headers).json()
        served: set[str] = set()
        for cat in categories:
            items = client.get("/api/v1/training/questions", headers=headers,
                               params={"category": cat["category"], "limit": 80, "shuffle": False}).json()
            served |= {item["text"] for item in items}
        mock = client.get("/api/v1/training/mock-exam", headers=headers).json()

    assert sum(cat["total"] for cat in categories) == len(QUESTIONS_TRAINING_FULL)
    assert served and not (served & official)
    assert mock["total_questions"] == 40
    assert not ({q["text"] for q in mock["questions"]} & official)
