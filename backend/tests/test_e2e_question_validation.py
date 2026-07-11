"""
Test E2E — Workflow de validation officielle des questions (certification DNTT).

  draft → submitted (admin) → approved / rejected (super_admin)
  Seules les questions approuvées sont tirées à l'examen réel.
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

ADMIN_EMAIL = f"qval-admin-{uuid.uuid4().hex[:8]}@test.gn"
ADMIN_PASS = "QValAdmin2026!"
SA_EMAIL = f"qval-sa-{uuid.uuid4().hex[:8]}@test.gn"
SA_PASS = "QValSuper2026!"


@pytest.fixture(scope="module")
def client():
    init_db()
    db = SessionLocal()
    db.add(User(id=str(uuid.uuid4()), email=ADMIN_EMAIL, full_name="Admin Val",
                password_hash=get_password_hash(ADMIN_PASS), role="admin", is_active=True))
    db.add(User(id=str(uuid.uuid4()), email=SA_EMAIL, full_name="Super Val",
                password_hash=get_password_hash(SA_PASS), role="super_admin", is_active=True))
    db.commit(); db.close()
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def draft_question() -> str:
    db = SessionLocal()
    q = Question(category="signalisation", text=f"Q validation {uuid.uuid4().hex[:6]}",
                 options=["A", "B"], correct_answer="A", is_active=True,
                 validation_status="draft")
    db.add(q); db.commit(); qid = q.id; db.close()
    return qid


def _login(client, email, pwd) -> str:
    r = client.post("/api/v1/auth/login", data={"username": email, "password": pwd},
                    headers={"Content-Type": "application/x-www-form-urlencoded"})
    return r.json()["access_token"]


def _auth(t): return {"Authorization": f"Bearer {t}"}


def test_cycle_complet_soumission_approbation(client: TestClient, draft_question: str):
    admin = _login(client, ADMIN_EMAIL, ADMIN_PASS)
    sa = _login(client, SA_EMAIL, SA_PASS)

    # 1. Admin soumet à validation
    r = client.post(f"/api/v1/questions/{draft_question}/submit-validation", headers=_auth(admin))
    assert r.status_code == 200, r.text[:200]
    assert r.json()["validation_status"] == "submitted"

    # 2. super_admin approuve
    r = client.post(f"/api/v1/questions/{draft_question}/approve", headers=_auth(sa))
    assert r.status_code == 200
    data = r.json()
    assert data["validation_status"] == "approved"
    assert data["validated_by"] is not None
    assert data["validated_at"] is not None


def test_rejet_avec_motif(client: TestClient, draft_question: str):
    admin = _login(client, ADMIN_EMAIL, ADMIN_PASS)
    sa = _login(client, SA_EMAIL, SA_PASS)
    client.post(f"/api/v1/questions/{draft_question}/submit-validation", headers=_auth(admin))
    r = client.post(f"/api/v1/questions/{draft_question}/reject",
                    json={"reason": "Formulation ambiguë, réponse contestable"}, headers=_auth(sa))
    assert r.status_code == 200
    assert r.json()["validation_status"] == "rejected"
    assert "ambiguë" in r.json()["rejection_reason"]


def test_admin_ne_peut_pas_approuver(client: TestClient, draft_question: str):
    """L'approbation est réservée au super_admin (autorité DNTT)."""
    admin = _login(client, ADMIN_EMAIL, ADMIN_PASS)
    r = client.post(f"/api/v1/questions/{draft_question}/approve", headers=_auth(admin))
    assert r.status_code == 403


def test_approuvee_ne_peut_etre_resoumise(client: TestClient, draft_question: str):
    admin = _login(client, ADMIN_EMAIL, ADMIN_PASS)
    sa = _login(client, SA_EMAIL, SA_PASS)
    client.post(f"/api/v1/questions/{draft_question}/submit-validation", headers=_auth(admin))
    client.post(f"/api/v1/questions/{draft_question}/approve", headers=_auth(sa))
    r = client.post(f"/api/v1/questions/{draft_question}/submit-validation", headers=_auth(admin))
    assert r.status_code == 409


def test_synthese_validation(client: TestClient):
    admin = _login(client, ADMIN_EMAIL, ADMIN_PASS)
    r = client.get("/api/v1/questions/validation-summary", headers=_auth(admin))
    assert r.status_code == 200
    data = r.json()
    assert "by_status" in data
    assert "category_coverage" in data
    assert "exam_ready" in data
    assert data["exam_questions_required"] == 40
