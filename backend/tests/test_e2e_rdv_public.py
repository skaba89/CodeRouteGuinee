"""
Test E2E — Parcours public complet :
inscription candidat libre → choix du centre → disponibilités → réservation.
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.db.session import SessionLocal, init_db
from app.models_center import Center
from app.models_session import ExamSession


@pytest.fixture(scope="module")
def client():
    init_db()
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="module")
def center_with_sessions():
    """Un centre avec 2 sessions futures : une large, une à 1 place."""
    db = SessionLocal()
    center = Center(
        id=str(uuid.uuid4()),
        name="Centre Test RDV",
        code=f"GN-TEST-RDV-{uuid.uuid4().hex[:6]}",
        city="Conakry", prefecture="Conakry", commune="Matam",
        address="Test", capacity=35, status="active",
    )
    db.add(center)
    tomorrow = datetime.now(UTC).replace(tzinfo=None) + timedelta(days=1)
    s_large = ExamSession(
        id=str(uuid.uuid4()),
        reference=f"SES-RDV-L-{uuid.uuid4().hex[:6]}",
        center_id=center.id, starts_at=tomorrow, capacity=35, status="open",
    )
    s_tiny = ExamSession(
        id=str(uuid.uuid4()),
        reference=f"SES-RDV-T-{uuid.uuid4().hex[:6]}",
        center_id=center.id, starts_at=tomorrow + timedelta(hours=3),
        capacity=1, status="open",
    )
    db.add_all([s_large, s_tiny])
    db.commit()
    ids = {"center_id": center.id, "large": s_large.id, "tiny": s_tiny.id}
    db.close()
    return ids


def _register(client: TestClient) -> dict:
    u = uuid.uuid4().hex[:8]
    r = client.post("/api/v1/registration/candidate", json={
        "first_name": "Rdv", "last_name": f"Test{u}",
        "email": f"rdv-{u}@test.gn", "password": "MotDePasse123!",
        "phone": f"+2246{u[:8]}", "identity_number": f"NNI-RDV-{u}",
        "permit_category": "B",
    })
    assert r.status_code == 201, r.text[:300]
    return r.json()


def _auth(tok: str) -> dict:
    return {"Authorization": f"Bearer {tok}"}


def test_parcours_inscription_puis_rdv(client: TestClient, center_with_sessions):
    ids = center_with_sessions
    reg = _register(client)
    tok = reg["access_token"]

    # 1. Disponibilités du centre choisi : 2 sessions avec places restantes
    r = client.get(f"/api/v1/bookings/availability/{ids['center_id']}", headers=_auth(tok))
    assert r.status_code == 200, r.text[:300]
    data = r.json()
    assert data["center"]["name"] == "Centre Test RDV"
    assert len(data["sessions"]) >= 2
    large = next(s for s in data["sessions"] if s["session_id"] == ids["large"])
    assert large["remaining_seats"] == 35 and large["full"] is False

    # 2. Réservation self-service
    r = client.post("/api/v1/bookings/self", json={"session_id": ids["large"]}, headers=_auth(tok))
    assert r.status_code == 201, r.text[:300]
    bk = r.json()
    assert bk["reference"] and bk["verification_code"]

    # 3. La place est décomptée
    r = client.get(f"/api/v1/bookings/availability/{ids['center_id']}", headers=_auth(tok))
    large = next(s for s in r.json()["sessions"] if s["session_id"] == ids["large"])
    assert large["remaining_seats"] == 34

    # 4. Une seule réservation active → 409
    r = client.post("/api/v1/bookings/self", json={"session_id": ids["tiny"]}, headers=_auth(tok))
    assert r.status_code == 409

    # 5. Mes réservations : visible avec centre et date
    r = client.get("/api/v1/bookings/my", headers=_auth(tok))
    assert r.status_code == 200
    mine = r.json()
    assert any(b["reference"] == bk["reference"] for b in mine)


def test_session_pleine_refusee(client: TestClient, center_with_sessions):
    ids = center_with_sessions
    # Candidat A remplit la session à 1 place
    a = _register(client)
    r = client.post("/api/v1/bookings/self", json={"session_id": ids["tiny"]}, headers=_auth(a["access_token"]))
    assert r.status_code == 201

    # Candidat B → complet
    b = _register(client)
    r = client.post("/api/v1/bookings/self", json={"session_id": ids["tiny"]}, headers=_auth(b["access_token"]))
    assert r.status_code == 409
    assert "complète" in r.json()["detail"]

    # La disponibilité reflète full=True
    r = client.get(f"/api/v1/bookings/availability/{ids['center_id']}", headers=_auth(b["access_token"]))
    tiny = next(s for s in r.json()["sessions"] if s["session_id"] == ids["tiny"])
    assert tiny["full"] is True and tiny["remaining_seats"] == 0


def test_session_inexistante_ou_passee(client: TestClient, center_with_sessions):
    reg = _register(client)
    tok = reg["access_token"]
    r = client.post("/api/v1/bookings/self", json={"session_id": "inexistant"}, headers=_auth(tok))
    assert r.status_code == 404

    # Session passée
    db = SessionLocal()
    past = ExamSession(
        id=str(uuid.uuid4()), reference=f"SES-PAST-{uuid.uuid4().hex[:6]}",
        center_id=center_with_sessions["center_id"],
        starts_at=datetime.now(UTC).replace(tzinfo=None) - timedelta(days=1),
        capacity=35, status="open",
    )
    db.add(past); db.commit(); past_id = past.id; db.close()
    r = client.post("/api/v1/bookings/self", json={"session_id": past_id}, headers=_auth(tok))
    assert r.status_code == 422
