"""
Tests pour les endpoints entries (coverage 61% → 90%+).
"""
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from fastapi.testclient import TestClient

from app.db.session import SessionLocal, init_db
from app.main import app
from app.models_center import Center
from app.models_session import ExamSession
from tests.conftest import get_admin_headers, get_center_headers


def _seed() -> tuple[str, str]:
    init_db()
    db = SessionLocal()
    suffix = uuid4().hex[:8]
    try:
        center = Center(code=f"CTR-ENT-{suffix}", name=f"Centre Entries {suffix}",
                        city="Conakry", address="Test", capacity=10, status="accredited")
        db.add(center)
        db.commit()
        db.refresh(center)
        session = ExamSession(reference=f"GN-ENT-{suffix}", center_id=center.id,
                              starts_at=datetime.now(UTC) + timedelta(days=1), capacity=10)
        db.add(session)
        db.commit()
        db.refresh(session)
        return center.code, session.id
    finally:
        db.close()


def test_entries_summary_and_logs() -> None:
    """GET /entries/summary et GET /entries/logs retournent des données valides."""
    with TestClient(app) as client:
        admin_headers = get_admin_headers(client)

        summary = client.get("/api/v1/entries/summary", headers=admin_headers)
        assert summary.status_code == 200
        s = summary.json()
        # Structure réelle de /entries/summary
        assert "total" in s or "total_validations" in s or "by_result" in s

        logs = client.get("/api/v1/entries/logs", headers=admin_headers)
        assert logs.status_code == 200
        assert isinstance(logs.json(), list)


def test_entry_validate_wrong_code() -> None:
    """POST /entries/validate avec mauvais code de vérification retourne denied."""
    center_code, session_id = _seed()
    suffix = uuid4().hex[:8]

    with TestClient(app) as client:
        admin_headers = get_admin_headers(client)
        center_headers = get_center_headers(client)

        cand = client.post("/api/v1/candidates", headers=admin_headers, json={
            "first_name": "Wrong", "last_name": f"Code-{suffix}",
            "identity_number": f"ID-WC-{suffix}", "phone": "+224621000001",
            "permit_category": "B",
        }).json()

        booking = client.post("/api/v1/bookings", headers=admin_headers, json={
            "candidate_id": cand["id"], "session_id": session_id,
        }).json()

        # Mauvais code de vérification
        r = client.post("/api/v1/entries/validate", headers=center_headers, json={
            "reference": booking["reference"],
            "verification_code": "WRONG-CODE",
            "center_code": center_code,
        })
        assert r.status_code == 200
        result = r.json()
        assert result["allowed"] is False


def test_entry_validate_full_flow() -> None:
    """Flux complet : entrée validée, puis doublon détecté."""
    center_code, session_id = _seed()
    suffix = uuid4().hex[:8]

    with TestClient(app) as client:
        admin_headers = get_admin_headers(client)
        center_headers = get_center_headers(client)

        cand = client.post("/api/v1/candidates", headers=admin_headers, json={
            "first_name": "Valid", "last_name": f"Entry-{suffix}",
            "identity_number": f"ID-VE-{suffix}", "phone": "+224621000002",
            "permit_category": "B",
        }).json()

        booking = client.post("/api/v1/bookings", headers=admin_headers, json={
            "candidate_id": cand["id"], "session_id": session_id,
        }).json()

        # Payer
        client.post("/api/v1/payments", headers=admin_headers, json={
            "booking_reference": booking["reference"],
            "amount_gnf": 250000, "provider": "orange_money", "phone": "+224621000002",
        })

        # Première entrée
        r1 = client.post("/api/v1/entries/validate", headers=center_headers, json={
            "reference": booking["reference"],
            "verification_code": booking["verification_code"],
            "center_code": center_code,
        })
        assert r1.status_code == 200
        assert r1.json()["allowed"] is True

        # Deuxième entrée — doublon
        r2 = client.post("/api/v1/entries/validate", headers=center_headers, json={
            "reference": booking["reference"],
            "verification_code": booking["verification_code"],
            "center_code": center_code,
        })
        assert r2.status_code == 200
        assert r2.json()["reason"] == "already_checked_in"


def test_entries_require_auth() -> None:
    """Les endpoints /entries requièrent une authentification."""
    with TestClient(app) as client:
        assert client.get("/api/v1/entries/summary").status_code == 401
        assert client.get("/api/v1/entries/logs").status_code == 401
        assert client.post("/api/v1/entries/validate", json={}).status_code == 401
