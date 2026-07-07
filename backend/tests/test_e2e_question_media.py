"""
Test E2E — Association d'un média (image/vidéo réelle) à une question.
N'altère jamais le texte/options/réponse : uniquement le média.
"""
from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.db.session import SessionLocal, init_db
from app.models_question import Question
from app.models_user import User
from app.security import get_password_hash

ADMIN_EMAIL = f"media-q-{uuid.uuid4().hex[:8]}@test.gn"
ADMIN_PASS = "MediaQAdmin2026!"


@pytest.fixture(scope="module")
def client():
    init_db()
    db = SessionLocal()
    db.add(User(id=str(uuid.uuid4()), email=ADMIN_EMAIL, full_name="Media Q Admin",
                password_hash=get_password_hash(ADMIN_PASS), role="admin", is_active=True))
    db.commit(); db.close()
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def question_id() -> str:
    db = SessionLocal()
    q = Question(category="signalisation", text=f"Question média {uuid.uuid4().hex[:6]}",
                 options=["Oui", "Non"], correct_answer="Oui", is_active=True)
    db.add(q); db.commit(); qid = q.id; db.close()
    return qid


def _login(client) -> str:
    r = client.post("/api/v1/auth/login",
                    data={"username": ADMIN_EMAIL, "password": ADMIN_PASS},
                    headers={"Content-Type": "application/x-www-form-urlencoded"})
    return r.json()["access_token"]


def _auth(t): return {"Authorization": f"Bearer {t}"}


def test_associer_image_reelle(client: TestClient, question_id: str):
    tok = _login(client)
    r = client.patch(f"/api/v1/questions/{question_id}/media", json={
        "media_type": "image",
        "media_url": "https://upload.wikimedia.org/panneau-stop.svg",
        "media_alt": "Panneau STOP officiel",
    }, headers=_auth(tok))
    assert r.status_code == 200, r.text[:300]
    data = r.json()
    assert data["media_type"] == "image"
    assert data["media_url"].startswith("https://")
    assert data["media_alt"] == "Panneau STOP officiel"
    # texte/options/réponse intacts
    assert data["options"] == ["Oui", "Non"]
    assert data["correct_answer"] == "Oui"


def test_associer_video(client: TestClient, question_id: str):
    tok = _login(client)
    r = client.patch(f"/api/v1/questions/{question_id}/media", json={
        "media_type": "video",
        "media_url": "https://cdn.example.gn/situation-conduite.mp4",
        "media_alt": "Situation de conduite",
    }, headers=_auth(tok))
    assert r.status_code == 200
    assert r.json()["media_type"] == "video"


def test_effacer_media_retour_svg(client: TestClient, question_id: str):
    tok = _login(client)
    # d'abord associer
    client.patch(f"/api/v1/questions/{question_id}/media", json={
        "media_type": "image", "media_url": "https://x.gn/a.jpg",
    }, headers=_auth(tok))
    # puis effacer
    r = client.patch(f"/api/v1/questions/{question_id}/media",
                     json={"media_url": None}, headers=_auth(tok))
    assert r.status_code == 200
    assert r.json()["media_url"] is None
    assert r.json()["media_type"] is None


def test_url_invalide_rejetee(client: TestClient, question_id: str):
    tok = _login(client)
    r = client.patch(f"/api/v1/questions/{question_id}/media",
                     json={"media_type": "image", "media_url": "javascript:alert(1)"},
                     headers=_auth(tok))
    assert r.status_code == 422


def test_question_inexistante(client: TestClient):
    tok = _login(client)
    r = client.patch("/api/v1/questions/inexistant/media",
                     json={"media_url": "https://x.gn/a.jpg"}, headers=_auth(tok))
    assert r.status_code == 404
