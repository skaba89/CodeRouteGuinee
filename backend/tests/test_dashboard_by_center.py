"""Test — tableau de bord territorial (supervision nationale DNTT)."""
from __future__ import annotations

import uuid

from fastapi.testclient import TestClient

from app.main import app
from app.db.session import init_db, SessionLocal
from app.models_center import Center
from tests.conftest import get_admin_headers, get_candidate_headers


def test_by_center_returns_national_and_per_center() -> None:
    init_db()
    db = SessionLocal()
    suffix = uuid.uuid4().hex[:6]
    for i in range(2):
        db.add(Center(id=f"bc-{suffix}-{i}", code=f"GN-BCT-{suffix}-{i}",
                      name=f"Centre {i}", city="Conakry", prefecture="Conakry",
                      commune="Kaloum", address="x", capacity=35, status="active"))
    db.commit(); db.close()

    with TestClient(app) as client:
        r = client.get("/api/v1/dashboard/by-center", headers=get_admin_headers(client))
        assert r.status_code == 200
        data = r.json()
        assert "national" in data and "centers" in data
        assert data["national"]["centers_total"] >= 2
        # Chaque centre expose les métriques attendues
        for c in data["centers"]:
            assert set(c) >= {"code", "name", "sessions", "bookings",
                              "exams_total", "pass_rate_pct", "open_incidents"}


def test_by_center_requires_admin() -> None:
    init_db()
    with TestClient(app) as client:
        r = client.get("/api/v1/dashboard/by-center", headers=get_candidate_headers(client))
        assert r.status_code == 403
