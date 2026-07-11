"""
Test — Protection anti double-paiement (idempotence financière).

Un booking déjà réglé ne peut JAMAIS être payé une seconde fois, quel que
soit le rôle (candidat ou admin). Protège les citoyens contre un double
débit (double-clic, relance réseau, requêtes concurrentes).
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app
from app.db.session import SessionLocal, init_db
from app.models_center import Center
from app.models_session import ExamSession
from tests.conftest import get_admin_headers


def _seed_center_and_session() -> str:
    init_db()
    db = SessionLocal()
    suffix = uuid4().hex[:8]
    try:
        center = Center(
            code=f"CTR-PAY-{suffix}", name="Centre Paiement", city="Conakry",
            address="Test", capacity=20, max_sessions_per_week=3, status="accredited",
        )
        db.add(center); db.commit(); db.refresh(center)
        session = ExamSession(
            reference=f"GN-SES-PAY-{suffix}", center_id=center.id,
            starts_at=datetime.now(UTC) + timedelta(days=7), capacity=20,
        )
        db.add(session); db.commit(); db.refresh(session)
        return session.id
    finally:
        db.close()


def test_double_paiement_bloque() -> None:
    session_id = _seed_center_and_session()
    suffix = uuid4().hex[:8]

    with TestClient(app) as client:
        admin_headers = get_admin_headers(client)

        candidate = client.post("/api/v1/candidates", json={
            "first_name": "Test", "last_name": f"Pay-{suffix}",
            "identity_number": f"GN-PAY-{suffix}", "phone": "+224622123456",
            "permit_category": "B",
        }, headers=admin_headers).json()

        booking = client.post("/api/v1/bookings", json={
            "candidate_id": candidate["id"], "session_id": session_id,
        }, headers=admin_headers).json()

        pay = {
            "booking_reference": booking["reference"], "amount_gnf": 250000,
            "provider": "orange_money", "phone": "+224622123456",
        }

        # 1er paiement → réussi
        r1 = client.post("/api/v1/payments", json=pay, headers=admin_headers)
        assert r1.status_code == 201
        assert r1.json()["status"] == "paid"

        # 2e paiement (double-clic / relance) → REFUSÉ (idempotence)
        r2 = client.post("/api/v1/payments", json=pay, headers=admin_headers)
        assert r2.status_code == 409, "le double-paiement doit être bloqué"

        # 3e tentative avec un autre provider → toujours refusé
        pay_wave = {**pay, "provider": "wave"}
        r3 = client.post("/api/v1/payments", json=pay_wave, headers=admin_headers)
        assert r3.status_code == 409


def test_un_seul_paiement_enregistre() -> None:
    """Après une tentative de double-paiement, un seul Payment paid existe."""
    session_id = _seed_center_and_session()
    suffix = uuid4().hex[:8]

    with TestClient(app) as client:
        admin_headers = get_admin_headers(client)
        candidate = client.post("/api/v1/candidates", json={
            "first_name": "Test", "last_name": f"Uniq-{suffix}",
            "identity_number": f"GN-UNIQ-{suffix}", "phone": "+224622999888",
            "permit_category": "B",
        }, headers=admin_headers).json()
        booking = client.post("/api/v1/bookings", json={
            "candidate_id": candidate["id"], "session_id": session_id,
        }, headers=admin_headers).json()
        pay = {
            "booking_reference": booking["reference"], "amount_gnf": 250000,
            "provider": "orange_money", "phone": "+224622999888",
        }
        client.post("/api/v1/payments", json=pay, headers=admin_headers)
        client.post("/api/v1/payments", json=pay, headers=admin_headers)
        client.post("/api/v1/payments", json=pay, headers=admin_headers)

    # Vérification en base : un seul paiement 'paid' pour ce booking
    from app.models_payment import Payment
    from sqlalchemy import select, func
    db = SessionLocal()
    n = db.scalar(
        select(func.count(Payment.id)).where(
            Payment.booking_reference == booking["reference"],
            Payment.status == "paid",
        )
    )
    db.close()
    assert n == 1, f"un seul paiement attendu, {n} trouvés"
