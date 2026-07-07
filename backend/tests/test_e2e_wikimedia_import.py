"""
Test E2E — Import des panneaux Wikimedia (domaine public) sur les questions.

Note : la validation d'URL fait de vraies requêtes réseau. Pour rester
hermétique, ces tests utilisent validate=false (applique le catalogue sans
requête). La logique de mapping et de préservation des médias manuels est
la même dans les deux modes.
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

ADMIN_EMAIL = f"wiki-import-{uuid.uuid4().hex[:8]}@test.gn"
ADMIN_PASS = "WikiImport2026!"


@pytest.fixture(scope="module")
def client():
    init_db()
    db = SessionLocal()
    db.add(User(id=str(uuid.uuid4()), email=ADMIN_EMAIL, full_name="Wiki Import Admin",
                password_hash=get_password_hash(ADMIN_PASS), role="super_admin", is_active=True))
    from app.seed_full import seed_questions
    if db.query(Question).count() < 50:
        seed_questions(db)
    db.commit(); db.close()
    with TestClient(app) as c:
        yield c


def _login(client) -> str:
    r = client.post("/api/v1/auth/login",
                    data={"username": ADMIN_EMAIL, "password": ADMIN_PASS},
                    headers={"Content-Type": "application/x-www-form-urlencoded"})
    return r.json()["access_token"]


def _auth(t): return {"Authorization": f"Bearer {t}"}


def test_import_wikimedia_associe_panneaux(client: TestClient):
    tok = _login(client)
    r = client.post("/api/v1/admin/ops/import-wikimedia-signs?validate=false", headers=_auth(tok))
    assert r.status_code == 200, r.text[:300]
    d = r.json()
    assert d["signs_available"] > 0
    assert d["questions_updated"] > 0

    # Des questions de signalisation ont maintenant une image Wikimedia
    db = SessionLocal()
    n = db.query(Question).filter(Question.media_url.like("%wikimedia%")).count()
    db.close()
    assert n > 0


def test_import_preserve_media_manuel(client: TestClient):
    """Un média posé manuellement par un admin ne doit PAS être écrasé."""
    tok = _login(client)
    # Question dédiée (indépendante de l'ordre des tests)
    db = SessionLocal()
    q = Question(category="signalisation", text=f"Question préservation {uuid.uuid4().hex[:6]}",
                 options=["A", "B"], correct_answer="A", is_active=True)
    db.add(q); db.commit(); qid = q.id; db.close()

    client.patch(f"/api/v1/questions/{qid}/media", json={
        "media_type": "image", "media_url": "https://mon-cdn.gn/panneau-perso.jpg",
        "media_alt": "Mon panneau",
    }, headers=_auth(tok))

    # Import Wikimedia
    client.post("/api/v1/admin/ops/import-wikimedia-signs?validate=false", headers=_auth(tok))

    # Le média manuel est conservé
    db = SessionLocal()
    url = db.get(Question, qid).media_url
    db.close()
    assert url == "https://mon-cdn.gn/panneau-perso.jpg", "le média manuel a été écrasé"


def test_import_interdit_aux_non_admins(client: TestClient):
    u = uuid.uuid4().hex[:6]
    cemail = f"na-{u}@test.gn"
    db = SessionLocal()
    db.add(User(id=str(uuid.uuid4()), email=cemail, full_name="Non Admin",
                password_hash=get_password_hash("NonAdmin2026!"), role="candidate", is_active=True))
    db.commit(); db.close()
    r = client.post("/api/v1/auth/login",
                    data={"username": cemail, "password": "NonAdmin2026!"},
                    headers={"Content-Type": "application/x-www-form-urlencoded"})
    tok = r.json()["access_token"]
    r = client.post("/api/v1/admin/ops/import-wikimedia-signs?validate=false", headers=_auth(tok))
    assert r.status_code == 403
