"""
Test E2E — Inscription publique d'une auto-école avec validation DNTT.

  1. L'auto-école s'inscrit publiquement → compte créé INACTIF
  2. Elle ne peut PAS se connecter (403 en attente de validation)
  3. Le super_admin l'active (PATCH status)
  4. Elle peut maintenant se connecter et inscrire un élève
"""
from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.db.session import SessionLocal, init_db
from app.models_user import User
from app.security import get_password_hash

SA_EMAIL = f"school-sa-{uuid.uuid4().hex[:8]}@test.gn"
SA_PASS = "SuperAdmin2026!School"


@pytest.fixture(scope="module")
def client():
    init_db()
    db = SessionLocal()
    db.add(User(
        id=str(uuid.uuid4()), email=SA_EMAIL, full_name="SA School",
        password_hash=get_password_hash(SA_PASS), role="super_admin", is_active=True,
    ))
    db.commit(); db.close()
    with TestClient(app) as c:
        yield c


def _login_status(client, email, password):
    return client.post("/api/v1/auth/login",
                       data={"username": email, "password": password},
                       headers={"Content-Type": "application/x-www-form-urlencoded"})


def _auth(t): return {"Authorization": f"Bearer {t}"}


def test_inscription_publique_ecole_avec_validation(client: TestClient):
    u = uuid.uuid4().hex[:8]
    email = f"ecole-pub-{u}@auto.gn"
    pwd = "EcolePubli2026!"

    # ── 1. Inscription publique → pending ────────────────────────────────
    r = client.post("/api/v1/registration/school", json={
        "school_name": "Auto-École de la Corniche",
        "manager_name": "Mamadou Diallo",
        "email": email, "phone": f"+22462{u[:7]}", "city": "Conakry",
        "password": pwd,
    })
    assert r.status_code == 201, r.text[:300]
    assert r.json()["status"] == "pending_validation"

    # ── 2. Connexion refusée (compte inactif) ────────────────────────────
    r = _login_status(client, email, pwd)
    assert r.status_code == 403
    assert "validation" in r.json()["detail"].lower()

    # ── 3. super_admin trouve le compte et l'active ──────────────────────
    sa = _login_status(client, SA_EMAIL, SA_PASS).json()["access_token"]
    r = client.get("/api/v1/users?role=driving_school", headers=_auth(sa))
    assert r.status_code == 200
    # la liste peut être paginée : {items:[...]} ou [...]
    payload = r.json()
    users = payload["items"] if isinstance(payload, dict) and "items" in payload else payload
    target = next(u2 for u2 in users if u2["email"] == email)
    assert target["is_active"] is False

    r = client.patch(f"/api/v1/users/{target['id']}/status",
                     json={"is_active": True, "reason": "Validation DNTT test"},
                     headers=_auth(sa))
    assert r.status_code == 200
    assert r.json()["is_active"] is True

    # ── 4. Connexion OK + inscription d'un élève ─────────────────────────
    r = _login_status(client, email, pwd)
    assert r.status_code == 200
    school_tok = r.json()["access_token"]

    r = client.post("/api/v1/registration/school-candidate", json={
        "first_name": "Premier", "last_name": f"Eleve{u}",
        "phone": f"+22463{u[:7]}", "identity_number": f"NNI-EL-{u}",
        "permit_category": "B",
    }, headers=_auth(school_tok))
    assert r.status_code == 201, r.text[:250]
    assert r.json()["candidate_reference"].startswith("GN-CODE-")


def test_inscription_ecole_refuse_doublon_email(client: TestClient):
    u = uuid.uuid4().hex[:8]
    body = {
        "school_name": "École Doublon", "manager_name": "Test Doublon",
        "email": f"doublon-{u}@auto.gn", "phone": f"+22464{u[:7]}",
        "city": "Kindia", "password": "DoublonPass2026!",
    }
    assert client.post("/api/v1/registration/school", json=body).status_code == 201
    # Même email → 409
    assert client.post("/api/v1/registration/school", json=body).status_code == 409
