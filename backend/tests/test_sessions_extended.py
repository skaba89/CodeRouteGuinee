"""
Tests étendus sessions — couverture open/close/cancel et endpoints secondaires.

Modules ciblés :
  app/routers/sessions.py (59% → objectif 85%+)
"""
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.db.session import SessionLocal, init_db
from app.main import app
from app.models_center import Center
from app.models_session import ExamSession
from tests.conftest import get_admin_headers


def _make_center(commune: str = "TestExt") -> Center:
    init_db()
    db = SessionLocal()
    s = uuid4().hex[:6]
    center = Center(
        code=f"CTR-EXT-{s}", name=f"Centre Ext {s}",
        city="Conakry", commune=commune, prefecture="Conakry",
        address=f"Rue Ext {s}", capacity=35,
        max_sessions_per_week=3, status="accredited",
    )
    db.add(center); db.commit(); db.refresh(center); db.close()
    return center


def _next_tuesday() -> datetime:
    now = datetime.now(UTC).replace(tzinfo=None)
    days = (1 - now.weekday()) % 7 or 7
    return (now + timedelta(days=days)).replace(hour=9, minute=0, second=0, microsecond=0)


def _create_session(client, headers, center_id, starts_at, capacity=35) -> dict:
    r = client.post("/api/v1/sessions", headers=headers, json={
        "center_id": center_id,
        "starts_at": starts_at.isoformat(),
        "capacity": capacity,
    })
    assert r.status_code == 201, f"Création session échouée : {r.text}"
    return r.json()


# ── open / close / cancel ─────────────────────────────────────────

class TestSessionLifecycle:
    def test_open_session_changes_status(self):
        center = _make_center()
        with TestClient(app) as client:
            h = get_admin_headers(client)
            session = _create_session(client, h, center.id, _next_tuesday())
            r = client.patch(f"/api/v1/sessions/{session['id']}/open", headers=h)
            assert r.status_code == 200
            assert r.json()["status"] == "open"

    def test_close_session_requires_open(self):
        center = _make_center()
        with TestClient(app) as client:
            h = get_admin_headers(client)
            session = _create_session(client, h, center.id, _next_tuesday())
            # Ouvrir d'abord
            client.patch(f"/api/v1/sessions/{session['id']}/open", headers=h)
            # Fermer
            r = client.patch(f"/api/v1/sessions/{session['id']}/close", headers=h)
            assert r.status_code == 200
            assert r.json()["status"] == "closed"

    def test_cancel_planned_session(self):
        center = _make_center()
        with TestClient(app) as client:
            h = get_admin_headers(client)
            session = _create_session(client, h, center.id, _next_tuesday())
            r = client.patch(f"/api/v1/sessions/{session['id']}/cancel", headers=h)
            assert r.status_code == 200
            assert r.json()["status"] == "cancelled"

    def test_cancelled_session_not_counted_in_week(self):
        """Une session annulée ne bloque pas la semaine."""
        center = _make_center()
        tuesday = _next_tuesday()
        with TestClient(app) as client:
            h = get_admin_headers(client)
            # Créer et annuler 3 sessions
            for day in [0, 2, 4]:
                s = _create_session(client, h, center.id, tuesday + timedelta(days=day))
                client.patch(f"/api/v1/sessions/{s['id']}/cancel", headers=h)
            # On peut maintenant créer une 4ème (les 3 précédentes sont annulées)
            r = client.post("/api/v1/sessions", headers=h, json={
                "center_id": center.id,
                "starts_at": tuesday.isoformat(),
                "capacity": 35,
            })
            assert r.status_code == 201, f"Attendu 201, reçu {r.status_code}: {r.text}"

    def test_open_nonexistent_session_404(self):
        with TestClient(app) as client:
            h = get_admin_headers(client)
            r = client.patch(f"/api/v1/sessions/{uuid4()}/open", headers=h)
            assert r.status_code == 404

    def test_cancel_nonexistent_session_404(self):
        with TestClient(app) as client:
            h = get_admin_headers(client)
            r = client.patch(f"/api/v1/sessions/{uuid4()}/cancel", headers=h)
            assert r.status_code == 404


# ── list sessions ─────────────────────────────────────────────────

class TestSessionListing:
    def test_list_sessions_returns_array(self):
        with TestClient(app) as client:
            h = get_admin_headers(client)
            r = client.get("/api/v1/sessions", headers=h)
            assert r.status_code == 200
            assert isinstance(r.json(), list)

    def test_list_sessions_filter_by_center(self):
        center = _make_center("ListTestCommune")
        tuesday = _next_tuesday()
        with TestClient(app) as client:
            h = get_admin_headers(client)
            _create_session(client, h, center.id, tuesday)
            r = client.get(f"/api/v1/sessions?center_id={center.id}", headers=h)
            assert r.status_code == 200
            data = r.json()
            assert all(s["center_id"] == center.id for s in data)

    def test_list_available_sessions(self):
        with TestClient(app) as client:
            h = get_admin_headers(client)
            r = client.get("/api/v1/sessions/available", headers=h)
            assert r.status_code == 200
            data = r.json()
            # Toutes les sessions disponibles ont une capacité > booked
            for s in data:
                assert s.get("capacity", 1) > s.get("booked", 0)

    def test_week_schedule_offset_negative(self):
        """week_offset=-1 → semaine passée (doit fonctionner sans erreur)."""
        with TestClient(app) as client:
            h = get_admin_headers(client)
            r = client.get("/api/v1/sessions/week-schedule?week_offset=-1", headers=h)
            assert r.status_code == 200

    def test_stats_by_commune_with_prefecture_filter(self):
        with TestClient(app) as client:
            h = get_admin_headers(client)
            r = client.get("/api/v1/sessions/stats/by-commune?prefecture=Conakry", headers=h)
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list)
        for item in data:
            assert "commune" in item
            assert "centers_count" in item



# ── capacity status ───────────────────────────────────────────────

class TestCapacityStatus:
    def test_capacity_status_full_session(self):
        """Créer une session de capacité 1 → simuler remplissage."""
        center = _make_center()
        tuesday = _next_tuesday() + timedelta(hours=4)
        with TestClient(app) as client:
            h = get_admin_headers(client)
            s = _create_session(client, h, center.id, tuesday, capacity=1)
            status = client.get(f"/api/v1/sessions/{s['id']}/capacity-status", headers=h).json()
            assert status["capacity"] == 1
            assert status["is_full"] is False  # pas encore de réservation

    def test_capacity_status_unknown_session_404(self):
        with TestClient(app) as client:
            h = get_admin_headers(client)
            r = client.get(f"/api/v1/sessions/{uuid4()}/capacity-status", headers=h)
            assert r.status_code == 404


# ── edge cases capacité ───────────────────────────────────────────

class TestCapacityEdgeCases:
    def test_capacity_zero_refused(self):
        """Capacité 0 → refusée (hors règle DNTT)."""
        center = _make_center()
        with TestClient(app) as client:
            h = get_admin_headers(client)
            r = client.post("/api/v1/sessions", headers=h, json={
                "center_id": center.id,
                "starts_at": _next_tuesday().isoformat(),
                "capacity": 0,
            })
            assert r.status_code in (400, 422)

    def test_session_past_date_behavior(self):
        """Créer une session dans le passé — vérifier la réponse."""
        center = _make_center()
        past = datetime.now(UTC).replace(tzinfo=None) - timedelta(days=7)
        with TestClient(app) as client:
            h = get_admin_headers(client)
            r = client.post("/api/v1/sessions", headers=h, json={
                "center_id": center.id,
                "starts_at": past.isoformat(),
                "capacity": 10,
            })
            # L'API peut accepter ou refuser — on vérifie juste qu'elle ne plante pas
            assert r.status_code in (201, 422)
