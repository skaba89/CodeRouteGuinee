"""
Tests E2E — Inscription candidat libre et candidats d'auto-école.
"""
from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.db.session import SessionLocal, init_db
from app.models_user import User
from app.security import get_password_hash


@pytest.fixture(scope="module")
def client():
    init_db()
    with TestClient(app) as c:
        yield c


def _uniq() -> str:
    return uuid.uuid4().hex[:8]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ── Candidat libre ───────────────────────────────────────────────────────────

def test_inscription_candidat_libre_complete(client: TestClient):
    u = _uniq()
    payload = {
        "first_name": "Aminata",
        "last_name": "Touré",
        "email": f"aminata-{u}@test.gn",
        "password": "MotDePasse123!",
        "phone": f"+22462{u[:7]}",
        "identity_number": f"NNI-{u}",
        "permit_category": "B",
        "city": "Conakry",
    }
    r = client.post("/api/v1/registration/candidate", json=payload)
    assert r.status_code == 201, r.text[:300]
    data = r.json()
    assert data["access_token"] and data["refresh_token"]
    assert data["candidate_reference"].startswith("GN-CODE-")

    # Connexion immédiate : /auth/me fonctionne avec le token retourné
    r = client.get("/api/v1/auth/me", headers=_auth(data["access_token"]))
    assert r.status_code == 200
    assert r.json()["role"] == "candidate"

    # La fiche candidat liée est accessible
    r = client.get("/api/v1/registration/my-profile", headers=_auth(data["access_token"]))
    assert r.status_code == 200
    prof = r.json()
    assert prof["reference"] == data["candidate_reference"]
    assert prof["first_name"] == "Aminata"


def test_inscription_libre_rejette_doublons(client: TestClient):
    u = _uniq()
    payload = {
        "first_name": "Sekou", "last_name": "Keita",
        "email": f"sekou-{u}@test.gn", "password": "MotDePasse123!",
        "phone": f"+22463{u[:7]}", "identity_number": f"NNI-{u}",
    }
    assert client.post("/api/v1/registration/candidate", json=payload).status_code == 201

    # Même email → 409
    p2 = dict(payload, phone=f"+22464{u[:7]}", identity_number=f"NNI2-{u}")
    assert client.post("/api/v1/registration/candidate", json=p2).status_code == 409

    # Même NNI, email différent → 409
    p3 = dict(payload, email=f"autre-{u}@test.gn", phone=f"+22465{u[:7]}")
    assert client.post("/api/v1/registration/candidate", json=p3).status_code == 409


def test_inscription_libre_valide_categorie(client: TestClient):
    u = _uniq()
    payload = {
        "first_name": "Test", "last_name": "Invalide",
        "email": f"cat-{u}@test.gn", "password": "MotDePasse123!",
        "phone": f"+22466{u[:7]}", "identity_number": f"NNI-CAT-{u}",
        "permit_category": "Z",
    }
    assert client.post("/api/v1/registration/candidate", json=payload).status_code == 422


# ── Auto-école ───────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def school_token(client: TestClient):
    u = _uniq()
    email = f"autoecole-{u}@test.gn"
    db = SessionLocal()
    db.add(User(
        id=str(uuid.uuid4()), email=email, full_name="Auto-École Test",
        password_hash=get_password_hash("EcolePass123!"),
        role="driving_school", is_active=True,
    ))
    db.commit(); db.close()
    r = client.post(
        "/api/v1/auth/login",
        data={"username": email, "password": "EcolePass123!"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert r.status_code == 200
    return r.json()["access_token"]


def test_autoecole_inscrit_candidat_sans_compte(client: TestClient, school_token: str):
    u = _uniq()
    r = client.post(
        "/api/v1/registration/school-candidate",
        json={
            "first_name": "Élève", "last_name": "SansCompte",
            "phone": f"+22467{u[:7]}", "identity_number": f"NNI-SC-{u}",
            "permit_category": "B",
        },
        headers=_auth(school_token),
    )
    assert r.status_code == 201, r.text[:300]
    data = r.json()
    assert data["candidate_reference"].startswith("GN-CODE-")
    assert data["has_login"] is False


def test_autoecole_inscrit_candidat_avec_compte(client: TestClient, school_token: str):
    u = _uniq()
    r = client.post(
        "/api/v1/registration/school-candidate",
        json={
            "first_name": "Élève", "last_name": "AvecCompte",
            "phone": f"+22468{u[:7]}", "identity_number": f"NNI-AC-{u}",
            "email": f"eleve-{u}@test.gn", "password": "ElevePass123!",
        },
        headers=_auth(school_token),
    )
    assert r.status_code == 201, r.text[:300]
    assert r.json()["has_login"] is True

    # L'élève peut se connecter et voir sa fiche
    r = client.post(
        "/api/v1/auth/login",
        data={"username": f"eleve-{u}@test.gn", "password": "ElevePass123!"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert r.status_code == 200
    tok = r.json()["access_token"]
    r = client.get("/api/v1/registration/my-profile", headers=_auth(tok))
    assert r.status_code == 200
    assert r.json()["last_name"] == "AvecCompte"


def test_autoecole_liste_ses_candidats(client: TestClient, school_token: str):
    r = client.get("/api/v1/registration/my-candidates", headers=_auth(school_token))
    assert r.status_code == 200
    data = r.json()
    assert data["total"] >= 2  # les 2 élèves inscrits ci-dessus
    names = {i["last_name"] for i in data["items"]}
    assert {"SansCompte", "AvecCompte"} <= names


def test_candidat_ne_peut_pas_inscrire_pour_ecole(client: TestClient):
    u = _uniq()
    r = client.post("/api/v1/registration/candidate", json={
        "first_name": "Simple", "last_name": "Candidat",
        "email": f"simple-{u}@test.gn", "password": "MotDePasse123!",
        "phone": f"+22469{u[:7]}", "identity_number": f"NNI-SIMPLE-{u}",
    })
    tok = r.json()["access_token"]
    r = client.post(
        "/api/v1/registration/school-candidate",
        json={
            "first_name": "X", "last_name": "Y",
            "phone": f"+22470{u[:7]}", "identity_number": f"NNI-X-{u}",
        },
        headers=_auth(tok),
    )
    assert r.status_code == 403
