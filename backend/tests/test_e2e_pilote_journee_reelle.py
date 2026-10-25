"""
Test E2E — Journée pilote réelle au centre DNTT Kaloum.

Simule le parcours production complet :
  1. Seed pilote via l'endpoint admin (sans Shell)
  2. Roster des convocations (référence + code de vérification)
  3. Login de l'agent centre
  4. Validation d'entrée du candidat (référence + code)
  5. Démarrage de l'examen depuis la réservation
  6. Récupération des 40 questions
  7. Réponses + soumission
  8. Résultats détaillés + statut
Ce test garantit que le pilote est fonctionnel de bout en bout.
"""
from __future__ import annotations

import os
import uuid

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.db.session import SessionLocal, init_db
from app.models_user import User
from app.security import get_password_hash
from app.seed_pilote_conakry import CENTRE_PILOTE


SUPER_EMAIL = f"pilote-sa-{uuid.uuid4().hex[:8]}@test.gn"
SUPER_PASS = "SuperAdminPilote2026!"


@pytest.fixture(scope="module")
def client():
    init_db()
    # Créer un super_admin de test
    db = SessionLocal()
    db.add(User(
        id=str(uuid.uuid4()),
        email=SUPER_EMAIL,
        full_name="SA Pilote Test",
        password_hash=get_password_hash(SUPER_PASS),
        role="super_admin",
        is_active=True,
    ))
    db.commit()
    db.close()
    with TestClient(app) as c:
        yield c


def _login(client: TestClient, email: str, password: str) -> str:
    r = client.post(
        "/api/v1/auth/login",
        data={"username": email, "password": password},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert r.status_code == 200, f"login {email} → {r.status_code}: {r.text[:200]}"
    return r.json()["access_token"]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def test_journee_pilote_complete(client: TestClient):
    # ── 1. Seed pilote via l'endpoint admin (pas de Shell nécessaire) ──────
    sa_token = _login(client, SUPER_EMAIL, SUPER_PASS)
    r = client.post("/api/v1/admin/ops/seed-pilote", headers=_auth(sa_token))
    assert r.status_code == 200, r.text[:300]
    assert r.json()["status"] == "ok", r.json()

    # Idempotence : relancer ne casse rien
    r2 = client.post("/api/v1/admin/ops/seed-pilote", headers=_auth(sa_token))
    assert r2.status_code == 200 and r2.json()["status"] == "ok"

    # ── 2. Roster des convocations ──────────────────────────────────────────
    r = client.get("/api/v1/admin/ops/pilote-roster", headers=_auth(sa_token))
    assert r.status_code == 200, r.text[:300]
    roster = r.json()
    assert roster["total"] >= 50, f"attendu ≥50 réservations, obtenu {roster['total']}"
    first = roster["items"][0]
    assert first["booking_reference"].startswith("BK-GN-CODE-B-PILOT-")
    assert len(first["verification_code"]) == 6

    # ── 2 bis. Encaissement espèces enregistré par la DNTT (import officiel) ─
    # Le pilote est payé en espèces au centre : les reçus sont importés par le
    # circuit officiel auditable avant le contrôle d'entrée (pas de faux paiement).
    r = client.post("/api/v1/payments/admin/import-official", headers=_auth(sa_token), json={
        "source": "pilote-kaloum-especes",
        "reason": "Reçus espèces de la journée pilote Kaloum",
        "payments": [{
            "booking_reference": first["booking_reference"],
            "amount_gnf": 150000,
            "provider": "especes",
            "phone": first.get("phone") or "+224620000000",
            "status": "paid",
            "receipt_number": f"ESP-{first['booking_reference']}",
        }],
    })
    assert r.status_code == 200, r.text[:300]

    # Identité contrôlée par la DNTT (préalable au contrôle d'entrée)
    from tests.conftest import verify_candidate_identity
    from app.models_booking import Booking
    with SessionLocal() as db:
        candidate_id = db.query(Booking).filter_by(reference=first["booking_reference"]).one().candidate_id
    verify_candidate_identity(client, candidate_id, _auth(sa_token), marker="pilote")

    # Prérequis du pilote : la banque chargée par seed-pilote n'a pas de média
    # exploitable ; l'autorité homologue une banque officielle avec médias.
    from tests.conftest import seed_media_ready_official_bank
    seed_media_ready_official_bank(client, _auth(sa_token), marker="pilote")

    # Le test se place le jour J : la session du candidat commence dans 5 min,
    # ce qui ouvre les fenêtres de contrôle d'entrée et de démarrage d'examen.
    from datetime import UTC, datetime, timedelta
    from app.models_session import ExamSession
    with SessionLocal() as db:
        booking = db.query(Booking).filter_by(reference=first["booking_reference"]).one()
        session = db.get(ExamSession, booking.session_id)
        session.starts_at = datetime.now(UTC).replace(tzinfo=None) + timedelta(minutes=5)
        db.commit()

    # ── 3. Login agent centre (créé par le seed) ────────────────────────────
    center_password = os.environ.get("PILOT_CENTER_PASSWORD", "KaloumDNTT2024!")
    center_token = _login(client, "centre.kaloum@dntt.gov.gn", center_password)

    # L'agent peut aussi consulter le roster
    r = client.get("/api/v1/admin/ops/pilote-roster", headers=_auth(center_token))
    assert r.status_code == 200

    # ── 4. Validation d'entrée du candidat (le jour J, à l'accueil) ─────────
    r = client.post(
        "/api/v1/entries/validate",
        json={
            "reference": first["booking_reference"],
            "verification_code": first["verification_code"],
            "center_code": CENTRE_PILOTE["code"],
        },
        headers=_auth(center_token),
    )
    assert r.status_code == 200, r.text[:300]
    entry = r.json()
    assert entry.get("allowed") is True, entry

    # Mauvais code → refus (anti-fraude)
    r = client.post(
        "/api/v1/entries/validate",
        json={"reference": first["booking_reference"], "verification_code": "XXXXXX"},
        headers=_auth(center_token),
    )
    assert r.status_code == 200 and r.json().get("allowed") is False

    # ── 5. Démarrage de l'examen depuis la réservation ──────────────────────
    r = client.post(
        "/api/v1/exams/start-from-booking",
        json={"booking_reference": first["booking_reference"]},
        headers=_auth(center_token),
    )
    assert r.status_code == 201, r.text[:300]
    attempt = r.json()
    attempt_id = attempt["id"]

    # ── 6. Les 40 questions de l'épreuve ────────────────────────────────────
    r = client.get(f"/api/v1/exams/{attempt_id}/questions", headers=_auth(center_token))
    assert r.status_code == 200, r.text[:300]
    questions = r.json()["questions"]
    assert len(questions) == 40, f"attendu 40 questions, obtenu {len(questions)}"
    # Chaque question a au moins 2 options non vides
    assert all(len(q.get("options", [])) >= 2 for q in questions)

    # ── 7. Réponses (première option partout) + soumission ──────────────────
    answers = {q["id"]: q["options"][0] for q in questions}
    r = client.post(
        f"/api/v1/exams/{attempt_id}/submit",
        json={"answers": answers},
        headers=_auth(center_token),
    )
    assert r.status_code == 200, r.text[:300]
    result = r.json()
    assert result["status"] in {"passed", "failed", "submitted", "completed"}, result
    assert "score" in result

    # ── 8. Résultats détaillés ───────────────────────────────────────────────
    r = client.get(f"/api/v1/exams/{attempt_id}/results", headers=_auth(center_token))
    assert r.status_code == 200, r.text[:300]
    detail = r.json()
    # L'agent de centre ne voit pas les bonnes réponses : fautes par thème seulement.
    assert detail["questions"] == []
    assert sum(theme["total"] for theme in detail["themes"]) == 40

    # ── 9. Statut de la tentative ────────────────────────────────────────────
    r = client.get(f"/api/v1/exams/{attempt_id}/status", headers=_auth(center_token))
    assert r.status_code == 200


def test_seed_pilote_refuse_sans_super_admin(client: TestClient):
    """L'agent centre ne peut pas déclencher le seed (super_admin only)."""
    center_password = os.environ.get("PILOT_CENTER_PASSWORD", "KaloumDNTT2024!")
    center_token = _login(client, "centre.kaloum@dntt.gov.gn", center_password)
    r = client.post("/api/v1/admin/ops/seed-pilote", headers=_auth(center_token))
    assert r.status_code == 403
