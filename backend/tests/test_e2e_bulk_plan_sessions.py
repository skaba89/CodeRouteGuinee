"""
Tests E2E — Planification en masse des sessions (règles DNTT).
"""
from __future__ import annotations

import uuid
from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.db.session import SessionLocal, init_db
from app.models_center import Center
from app.models_user import User
from app.security import get_password_hash


ADMIN_EMAIL = f"plan-admin-{uuid.uuid4().hex[:8]}@test.gn"
ADMIN_PASS = "PlanAdmin2026!"


@pytest.fixture(scope="module")
def client():
    init_db()
    db = SessionLocal()
    db.add(User(
        id=str(uuid.uuid4()), email=ADMIN_EMAIL, full_name="Plan Admin",
        password_hash=get_password_hash(ADMIN_PASS), role="super_admin", is_active=True,
    ))
    db.commit(); db.close()
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="module")
def admin_token(client: TestClient) -> str:
    r = client.post(
        "/api/v1/auth/login",
        data={"username": ADMIN_EMAIL, "password": ADMIN_PASS},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert r.status_code == 200
    return r.json()["access_token"]


@pytest.fixture()
def fresh_center() -> str:
    db = SessionLocal()
    center = Center(
        id=str(uuid.uuid4()), name=f"Centre Plan {uuid.uuid4().hex[:4]}",
        code=f"GN-PLAN-{uuid.uuid4().hex[:6]}",
        city="Kindia", prefecture="Kindia", commune="Kindia Centre",
        address="Test", capacity=35, status="active",
    )
    db.add(center); db.commit()
    cid = center.id; db.close()
    return cid


def _auth(tok: str) -> dict:
    return {"Authorization": f"Bearer {tok}"}


def test_bulk_plan_respecte_regle_3_par_semaine(client, admin_token, fresh_center):
    """4 créneaux demandés par semaine → 3 créés (règle DNTT), 1 refusé."""
    # Partir d'un lundi futur garantit que lundi ET mercredi tombent
    # dans la fenêtre (sinon le lundi de la 1re semaine peut être passé).
    today = date.today()
    next_monday = today + timedelta(days=(7 - today.weekday()) + 7)  # lundi 2 semaines plus loin
    r = client.post(
        "/api/v1/sessions/bulk-plan",
        json={
            "center_id": fresh_center,
            "weeks": 2,
            "weekdays": [0, 2],   # lundi, mercredi
            "hours": [9, 14],     # 2 créneaux/jour → 4 par semaine demandés
            "capacity": 35,
            "start_from": next_monday.isoformat(),
        },
        headers=_auth(admin_token),
    )
    assert r.status_code == 201, r.text[:300]
    data = r.json()
    # 2 semaines × max 3 par semaine = 6 créées, 2 refusées
    assert data["created_count"] == 6, data
    assert data["skipped_count"] == 2
    assert all("max 3 sessions/semaine" in s["reason"] for s in data["skipped"])

    # Visibles dans la vue admin du centre
    r = client.get(f"/api/v1/sessions/upcoming-by-center/{fresh_center}", headers=_auth(admin_token))
    assert r.status_code == 200
    assert r.json()["total"] == 6


def test_bulk_plan_refuse_chevauchement(client, admin_token, fresh_center):
    """Re-planifier les mêmes créneaux → tout est refusé (chevauchement)."""
    # start_from aligné sur un mardi futur (weekday=1), sinon le créneau
    # unique demandé tombe hors de la fenêtre de la semaine.
    today = date.today()
    next_tuesday = today + timedelta(days=(1 - today.weekday()) % 7 + 21)
    body = {
        "center_id": fresh_center,
        "weeks": 1,
        "weekdays": [1],  # mardi
        "hours": [10],
        "start_from": next_tuesday.isoformat(),
    }
    r1 = client.post("/api/v1/sessions/bulk-plan", json=body, headers=_auth(admin_token))
    assert r1.status_code == 201 and r1.json()["created_count"] == 1

    r2 = client.post("/api/v1/sessions/bulk-plan", json=body, headers=_auth(admin_token))
    assert r2.status_code == 201
    assert r2.json()["created_count"] == 0
    assert r2.json()["skipped_count"] == 1
    assert "chevauchement" in r2.json()["skipped"][0]["reason"]


def test_bulk_plan_valide_entrees(client, admin_token, fresh_center):
    # Centre inexistant → 404
    r = client.post(
        "/api/v1/sessions/bulk-plan",
        json={"center_id": "inexistant", "weeks": 1, "weekdays": [0], "hours": [9]},
        headers=_auth(admin_token),
    )
    assert r.status_code == 404

    # Heure hors plage → 422
    r = client.post(
        "/api/v1/sessions/bulk-plan",
        json={"center_id": fresh_center, "weeks": 1, "weekdays": [0], "hours": [22]},
        headers=_auth(admin_token),
    )
    assert r.status_code == 422


def test_bulk_plan_interdit_aux_non_admins(client, fresh_center):
    u = uuid.uuid4().hex[:8]
    r = client.post("/api/v1/registration/candidate", json={
        "first_name": "Pas", "last_name": "Admin",
        "email": f"pasadmin-{u}@test.gn", "password": "MotDePasse123!",
        "phone": f"+2246{u[:8]}", "identity_number": f"NNI-PA-{u}",
    })
    tok = r.json()["access_token"]
    r = client.post(
        "/api/v1/sessions/bulk-plan",
        json={"center_id": fresh_center, "weeks": 1, "weekdays": [0], "hours": [9]},
        headers=_auth(tok),
    )
    assert r.status_code == 403
