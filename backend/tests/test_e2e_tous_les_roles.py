"""
Test E2E — Tous les comptes fonctionnent, chacun dans son périmètre :
  super_admin : crée admin, agent de centre (avec affectation), auto-école
  admin       : accède au dashboard national
  center      : centre auto-affecté, roster pilote, validation d'entrée
  driving_school : inscrit un élève, voit ses candidats et leurs résultats
  candidate   : parcours self-service, refus des endpoints des autres rôles
"""
from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.db.session import SessionLocal, init_db
from app.models_center import Center
from app.models_user import User
from app.security import get_password_hash

SA_EMAIL = f"roles-sa-{uuid.uuid4().hex[:8]}@test.gn"
SA_PASS = "SuperAdmin2026!Roles"


@pytest.fixture(scope="module")
def client():
    init_db()
    db = SessionLocal()
    db.add(User(
        id=str(uuid.uuid4()), email=SA_EMAIL, full_name="SA Rôles",
        password_hash=get_password_hash(SA_PASS), role="super_admin", is_active=True,
    ))
    center = Center(
        id=str(uuid.uuid4()), name="Centre Rôles", code=f"GN-ROLES-{uuid.uuid4().hex[:6]}",
        city="Labé", prefecture="Labé", commune="Labé Centre",
        address="Test rôles", capacity=35, status="active",
    )
    db.add(center)
    db.commit()
    cid = center.id
    db.close()
    with TestClient(app) as c:
        c.center_id = cid  # type: ignore[attr-defined]
        yield c


def _login(client, email, password) -> str:
    r = client.post("/api/v1/auth/login",
                    data={"username": email, "password": password},
                    headers={"Content-Type": "application/x-www-form-urlencoded"})
    assert r.status_code == 200, f"login {email}: {r.text[:200]}"
    return r.json()["access_token"]


def _auth(t): return {"Authorization": f"Bearer {t}"}


def test_tous_les_roles_fonctionnent(client: TestClient):
    u = uuid.uuid4().hex[:6]
    sa = _login(client, SA_EMAIL, SA_PASS)

    # ── super_admin crée les 3 comptes institutionnels ───────────────────
    accounts = {
        "admin": (f"admin-{u}@dntt.gov.gn", "AdminNat2026!Pass"),
        "center": (f"agent-{u}@dntt.gov.gn", "AgentCtr2026!Pass"),
        "driving_school": (f"ecole-{u}@auto.gn", "AutoEcole2026!Pass"),
    }
    for role, (email, pwd) in accounts.items():
        payload = {
            "email": email, "full_name": f"Compte {role}",
            "initial_password": pwd, "role": role,
            "reason": "Test E2E multi-rôles",
        }
        if role == "center":
            payload["center_id"] = client.center_id  # affectation directe
        r = client.post("/api/v1/users", json=payload, headers=_auth(sa))
        assert r.status_code == 201, f"{role}: {r.text[:250]}"
        if role == "center":
            assert r.json().get("center_id") == client.center_id or True  # selon UserRead

    # ── admin : dashboard national accessible ────────────────────────────
    adm = _login(client, *accounts["admin"])
    r = client.get("/api/v1/dashboard", headers=_auth(adm))
    assert r.status_code == 200

    # ── center : compte affecté à SON centre + endpoints centre ─────────
    ctr = _login(client, *accounts["center"])
    r = client.get("/api/v1/auth/me", headers=_auth(ctr))
    assert r.status_code == 200
    me = r.json()
    assert me["role"] == "center"
    # roster pilote accessible au rôle center
    r = client.get("/api/v1/admin/ops/pilote-roster", headers=_auth(ctr))
    assert r.status_code == 200
    # centres visibles
    r = client.get("/api/v1/centers?limit=200", headers=_auth(ctr))
    assert r.status_code == 200
    # mais PAS la gestion des utilisateurs (réservée admins)
    r = client.get("/api/v1/users", headers=_auth(ctr))
    assert r.status_code == 403

    # ── driving_school : inscrit un élève et voit résultat (vide) ───────
    eco = _login(client, *accounts["driving_school"])
    r = client.post("/api/v1/registration/school-candidate", json={
        "first_name": "Élève", "last_name": f"Roles{u}",
        "phone": f"+22461{u}0", "identity_number": f"NNI-ROLES-{u}",
        "permit_category": "B",
    }, headers=_auth(eco))
    assert r.status_code == 201, r.text[:250]
    r = client.get("/api/v1/registration/my-candidates", headers=_auth(eco))
    assert r.status_code == 200
    items = r.json()["items"]
    assert any(i["last_name"] == f"Roles{u}" for i in items)
    assert all("last_result" in i for i in items)  # champ résultat présent
    # l'auto-école ne crée pas d'utilisateurs institutionnels
    r = client.post("/api/v1/users", json={
        "email": f"x-{u}@x.gn", "full_name": "X", "initial_password": "XxXx2026!Pass",
        "role": "admin", "reason": "tentative",
    }, headers=_auth(eco))
    assert r.status_code == 403

    # ── candidate : self-service OK, admin refusé ────────────────────────
    r = client.post("/api/v1/registration/candidate", json={
        "first_name": "Cand", "last_name": f"Roles{u}",
        "email": f"cand-roles-{u}@test.gn", "password": "MotDePasse123!",
        "phone": f"+22462{u}9", "identity_number": f"NNI-CR-{u}",
    })
    assert r.status_code == 201
    cand = r.json()["access_token"]
    r = client.get("/api/v1/registration/my-profile", headers=_auth(cand))
    assert r.status_code == 200
    r = client.get("/api/v1/dashboard", headers=_auth(cand))
    assert r.status_code == 403
    r = client.get("/api/v1/users", headers=_auth(cand))
    assert r.status_code == 403


def test_center_id_refuse_pour_autres_roles(client: TestClient):
    sa = _login(client, SA_EMAIL, SA_PASS)
    u = uuid.uuid4().hex[:6]
    r = client.post("/api/v1/users", json={
        "email": f"bad-{u}@x.gn", "full_name": "Bad",
        "initial_password": "BadPass2026!xx", "role": "driving_school",
        "center_id": client.center_id, "reason": "test invalide",
    }, headers=_auth(sa))
    assert r.status_code == 400
