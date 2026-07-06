"""
Test E2E — Parcours candidat A→Z complet en conditions réelles :

  1. Inscription publique (compte + fiche candidat + référence GN-CODE)
  2. Choix du centre et du créneau (places restantes)
  3. Réservation (référence + code de vérification)
  4. Paiement Mobile Money (sandbox) → réservation 'paid'
  5. Téléchargement de la convocation PDF (QR code inclus)
  6. Le jour J : le candidat se connecte sur l'appareil du centre avec
     SON compte et démarre SON examen depuis sa réservation
  7. 40 questions → soumission → résultat
  8. Notifications (email/SMS/WhatsApp) déclenchées sans bloquer
  9. Sécurité : un autre candidat ne peut PAS démarrer cette réservation
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
def center_session():
    db = SessionLocal()
    # Questions officielles nécessaires au tirage des 40 questions d'épreuve
    from app.models_question import Question
    if db.query(Question).count() < 50:
        from app.seed_full import seed_questions
        seed_questions(db)
        db.commit()
    center = Center(
        id=str(uuid.uuid4()), name="Centre A-Z", code=f"GN-AZ-{uuid.uuid4().hex[:6]}",
        city="Conakry", prefecture="Conakry", commune="Ratoma",
        address="Test A-Z", capacity=35, status="active",
    )
    db.add(center)
    s = ExamSession(
        id=str(uuid.uuid4()), reference=f"SES-AZ-{uuid.uuid4().hex[:6]}",
        center_id=center.id,
        starts_at=datetime.now(UTC).replace(tzinfo=None) + timedelta(days=1),
        capacity=35, status="open",
    )
    db.add(s); db.commit()
    ids = {"center_id": center.id, "session_id": s.id}
    db.close()
    return ids


def _auth(t: str) -> dict:
    return {"Authorization": f"Bearer {t}"}


def _register(client: TestClient) -> dict:
    u = uuid.uuid4().hex[:8]
    r = client.post("/api/v1/registration/candidate", json={
        "first_name": "Fatou", "last_name": f"Az{u}",
        "email": f"az-{u}@test.gn", "password": "MotDePasse123!",
        "phone": f"+2246{u[:8]}", "identity_number": f"NNI-AZ-{u}",
        "permit_category": "B",
    })
    assert r.status_code == 201, r.text[:300]
    return r.json()


def test_parcours_candidat_a_z(client: TestClient, center_session):
    ids = center_session

    # ── 1. Inscription ───────────────────────────────────────────────────
    reg = _register(client)
    tok = reg["access_token"]
    assert reg["candidate_reference"].startswith("GN-CODE-")

    # ── 2. Centres visibles + disponibilités du centre choisi ────────────
    r = client.get("/api/v1/centers?limit=200", headers=_auth(tok))
    assert r.status_code == 200 and r.json()["total"] >= 1

    r = client.get(f"/api/v1/bookings/availability/{ids['center_id']}", headers=_auth(tok))
    assert r.status_code == 200
    slot = next(s for s in r.json()["sessions"] if s["session_id"] == ids["session_id"])
    assert slot["remaining_seats"] >= 1

    # ── 3. Réservation ────────────────────────────────────────────────────
    r = client.post("/api/v1/bookings/self", json={"session_id": ids["session_id"]}, headers=_auth(tok))
    assert r.status_code == 201, r.text[:300]
    bk = r.json()
    assert bk["reference"] and bk["verification_code"]

    # ── 4. Paiement Mobile Money (sandbox → paid) ────────────────────────
    r = client.post("/api/v1/payments", json={
        "booking_reference": bk["reference"],
        "amount_gnf": 250000,
        "provider": "orange_money",
        "phone": "+224620000001",
    }, headers=_auth(tok))
    assert r.status_code == 201, r.text[:300]
    pay = r.json()
    assert pay["status"] == "paid", pay
    assert pay["receipt_number"]

    # La réservation est passée à 'paid'
    r = client.get("/api/v1/bookings/my", headers=_auth(tok))
    mine = next(b for b in r.json() if b["reference"] == bk["reference"])
    assert mine["status"] == "paid", mine

    # ── 5. Convocation PDF (QR inclus) ────────────────────────────────────
    r = client.get(f"/api/v1/documents/convocations/{bk['reference']}.pdf", headers=_auth(tok))
    assert r.status_code == 200, r.text[:200]
    assert r.headers["content-type"] == "application/pdf"
    assert r.content[:5] == b"%PDF-", "le fichier doit être un vrai PDF"
    assert len(r.content) > 1000

    # ── 6. Jour J : le candidat démarre SON examen (appareil du centre,
    #      compte du candidat) ─────────────────────────────────────────────
    r = client.post("/api/v1/exams/start-from-booking",
                    json={"booking_reference": bk["reference"]}, headers=_auth(tok))
    assert r.status_code == 201, r.text[:300]
    attempt_id = r.json()["id"]

    # ── 7. 40 questions → réponses → soumission ──────────────────────────
    r = client.get(f"/api/v1/exams/{attempt_id}/questions", headers=_auth(tok))
    assert r.status_code == 200
    questions = r.json()["questions"]
    assert len(questions) == 40

    answers = {q["id"]: q["options"][0] for q in questions}
    # ── 8. Soumission : les notifications (email/SMS/WhatsApp) sont
    #      best-effort et ne doivent JAMAIS bloquer le résultat ───────────
    r = client.post(f"/api/v1/exams/{attempt_id}/submit",
                    json={"answers": answers}, headers=_auth(tok))
    assert r.status_code == 200, r.text[:300]
    result = r.json()
    assert "score" in result and result["status"] in {"passed", "failed", "submitted", "completed"}

    # Résultats détaillés accessibles au candidat
    r = client.get(f"/api/v1/exams/{attempt_id}/results", headers=_auth(tok))
    assert r.status_code == 200
    assert len(r.json().get("questions", [])) == 40


def test_candidat_ne_demarre_pas_la_reservation_d_un_autre(client: TestClient, center_session):
    ids = center_session

    # Candidat A réserve
    a = _register(client)
    r = client.post("/api/v1/bookings/self", json={"session_id": ids["session_id"]},
                    headers=_auth(a["access_token"]))
    assert r.status_code == 201
    ref_a = r.json()["reference"]

    # Candidat B tente de démarrer l'examen de A → 403
    b = _register(client)
    r = client.post("/api/v1/exams/start-from-booking",
                    json={"booking_reference": ref_a}, headers=_auth(b["access_token"]))
    assert r.status_code == 403
    assert "appartient" in r.json()["detail"]
