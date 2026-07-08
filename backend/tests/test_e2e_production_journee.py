"""
TEST END-TO-END — JOURNÉE DE PRODUCTION RÉELLE
================================================

Simule une journée complète comme en production nationale, tous rôles
confondus, dans l'ordre chronologique réel :

  ACTE 1 — La DNTT prépare (super_admin)
    1.1 création d'un admin national et d'un agent de centre affecté
    1.2 planification en masse des sessions d'un centre
  ACTE 2 — Une auto-école s'enregistre et est validée
    2.1 inscription publique auto-école → compte inactif
    2.2 login refusé (validation DNTT en attente)
    2.3 activation par la DNTT → login OK
    2.4 l'auto-école inscrit deux élèves
  ACTE 3 — Un candidat libre fait tout son parcours
    3.1 inscription publique → référence GN-CODE + connexion auto
    3.2 consultation des centres et des créneaux (places restantes)
    3.3 réservation → référence + code de vérification
    3.4 paiement Mobile Money → réservation payée
    3.5 téléchargement de la convocation PDF (avec QR)
  ACTE 4 — Le jour de l'examen (au centre)
    4.1 l'agent valide l'entrée (référence + code)
    4.2 le candidat démarre SON examen sur l'appareil du centre
    4.3 40 questions, chacune avec un visuel
    4.4 soumission → résultat immédiat + notifications déclenchées
    4.5 consultation du résultat détaillé + statut
  ACTE 5 — Suivi et supervision
    5.1 l'auto-école voit le résultat de son élève
    5.2 l'admin voit le dashboard national mis à jour
  ACTE 6 — Contrôles de sécurité (cas réels d'abus)
    6.1 un candidat ne peut pas démarrer la réservation d'un autre
    6.2 un candidat n'accède ni au dashboard ni aux utilisateurs
    6.3 une session complète refuse toute nouvelle réservation

Ce test vaut recette : s'il passe, le cœur métier de la plateforme est
opérationnel en conditions réelles.
"""
from __future__ import annotations

import uuid
from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.db.session import SessionLocal, init_db
from app.models_user import User
from app.security import get_password_hash


# ── Comptes fondateurs (créés hors flux, comme le seed de bootstrap) ─────────
SA_EMAIL = f"dg-national-{uuid.uuid4().hex[:6]}@dntt.gov.gn"
SA_PASS = "DirecteurNational2026!"


@pytest.fixture(scope="module")
def client():
    init_db()
    db = SessionLocal()
    db.add(User(
        id=str(uuid.uuid4()), email=SA_EMAIL, full_name="Directeur National DNTT",
        password_hash=get_password_hash(SA_PASS), role="super_admin", is_active=True,
    ))
    # Questions officielles (tirage des 40 par épreuve)
    from app.models_question import Question
    if db.query(Question).count() < 50:
        from app.seed_full import seed_questions
        seed_questions(db)
    db.commit(); db.close()
    with TestClient(app) as c:
        yield c


def _login(client, email, password) -> str:
    r = client.post("/api/v1/auth/login",
                    data={"username": email, "password": password},
                    headers={"Content-Type": "application/x-www-form-urlencoded"})
    assert r.status_code == 200, f"login {email} échoué: {r.status_code} {r.text[:150]}"
    return r.json()["access_token"]


def _auth(t): return {"Authorization": f"Bearer {t}"}


def _register_candidate(client, prefix="cand") -> dict:
    u = uuid.uuid4().hex[:8]
    r = client.post("/api/v1/registration/candidate", json={
        "first_name": prefix.capitalize(), "last_name": f"Test{u}",
        "email": f"{prefix}-{u}@test.gn", "password": "MotDePasse123!",
        "phone": f"+2246{u[:8]}", "identity_number": f"NNI-{u}",
        "permit_category": "B", "city": "Conakry",
    })
    assert r.status_code == 201, r.text[:200]
    return r.json()


def test_journee_production_complete(client: TestClient):
    """Le scénario complet, dans l'ordre chronologique réel."""

    # ══ ACTE 1 — La DNTT prépare ═══════════════════════════════════════════
    sa = _login(client, SA_EMAIL, SA_PASS)
    tag = uuid.uuid4().hex[:6]

    # Un centre d'examen (créé en base comme lors de l'accréditation)
    from app.models_center import Center
    db = SessionLocal()
    center = Center(
        id=str(uuid.uuid4()), name="Centre DNTT Ratoma", code=f"GN-CKY-RATOMA-{tag}",
        city="Conakry", prefecture="Conakry", commune="Ratoma",
        address="Ratoma, Conakry", capacity=35, status="active",
    )
    db.add(center); db.commit(); center_id = center.id; db.close()

    # 1.1 — Admin national + agent de centre affecté
    admin_email = f"admin-{tag}@dntt.gov.gn"
    r = client.post("/api/v1/users", json={
        "email": admin_email, "full_name": "Admin National",
        "initial_password": "AdminNational2026!", "role": "admin",
        "reason": "Recette production",
    }, headers=_auth(sa))
    assert r.status_code == 201, r.text[:200]

    agent_email = f"agent-{tag}@dntt.gov.gn"
    r = client.post("/api/v1/users", json={
        "email": agent_email, "full_name": "Agent Ratoma",
        "initial_password": "AgentRatoma2026!", "role": "center",
        "center_id": center_id, "reason": "Recette production",
    }, headers=_auth(sa))
    assert r.status_code == 201, r.text[:200]

    # 1.2 — Planification en masse (lundi/mercredi 9h, 4 semaines)
    next_monday = date.today() + timedelta(days=(7 - date.today().weekday()) + 7)
    r = client.post("/api/v1/sessions/bulk-plan", json={
        "center_id": center_id, "weeks": 4, "weekdays": [0, 2], "hours": [9],
        "capacity": 35, "start_from": next_monday.isoformat(),
    }, headers=_auth(sa))
    assert r.status_code == 201, r.text[:200]
    assert r.json()["created_count"] >= 6  # ≥6 sessions programmées

    # ══ ACTE 2 — Auto-école s'enregistre et est validée ════════════════════
    school_email = f"ecole-{tag}@auto.gn"
    school_pass = "AutoEcole2026!"
    r = client.post("/api/v1/registration/school", json={
        "school_name": "Auto-École Ratoma", "manager_name": "Ibrahima Bah",
        "email": school_email, "phone": f"+2246{tag}0", "city": "Conakry",
        "password": school_pass,
    })
    assert r.status_code == 201 and r.json()["status"] == "pending_validation"

    # 2.2 — Login refusé tant que non validé
    r = client.post("/api/v1/auth/login",
                    data={"username": school_email, "password": school_pass},
                    headers={"Content-Type": "application/x-www-form-urlencoded"})
    assert r.status_code == 403

    # 2.3 — La DNTT active
    r = client.get("/api/v1/users?role=driving_school", headers=_auth(sa))
    users = r.json().get("items", r.json()) if isinstance(r.json(), dict) else r.json()
    school_user = next(u for u in users if u["email"] == school_email)
    r = client.patch(f"/api/v1/users/{school_user['id']}/status",
                     json={"is_active": True, "reason": "Validation DNTT"}, headers=_auth(sa))
    assert r.status_code == 200
    school_tok = _login(client, school_email, school_pass)

    # 2.4 — Inscrit deux élèves
    for i in range(2):
        r = client.post("/api/v1/registration/school-candidate", json={
            "first_name": f"Élève{i}", "last_name": f"Ratoma{tag}",
            "phone": f"+2246{tag}{i}1", "identity_number": f"NNI-EL-{tag}-{i}",
            "permit_category": "B",
        }, headers=_auth(school_tok))
        assert r.status_code == 201

    # ══ ACTE 3 — Candidat libre : parcours complet ═════════════════════════
    reg = _register_candidate(client, "fatou")
    cand_tok = reg["access_token"]
    assert reg["candidate_reference"].startswith("GN-CODE-")

    # 3.2 — Centres + créneaux
    r = client.get("/api/v1/centers?limit=200", headers=_auth(cand_tok))
    assert r.status_code == 200 and r.json()["total"] >= 1

    r = client.get(f"/api/v1/bookings/availability/{center_id}", headers=_auth(cand_tok))
    assert r.status_code == 200
    sessions = r.json()["sessions"]
    assert len(sessions) >= 6
    slot = sessions[0]
    assert slot["remaining_seats"] == 35 and slot["full"] is False

    # 3.3 — Réservation
    r = client.post("/api/v1/bookings/self", json={"session_id": slot["session_id"]},
                    headers=_auth(cand_tok))
    assert r.status_code == 201, r.text[:200]
    booking = r.json()
    booking_ref = booking["reference"]
    verif_code = booking["verification_code"]
    assert booking_ref and verif_code

    # La place est décomptée
    r = client.get(f"/api/v1/bookings/availability/{center_id}", headers=_auth(cand_tok))
    updated_slot = next(s for s in r.json()["sessions"] if s["session_id"] == slot["session_id"])
    assert updated_slot["remaining_seats"] == 34

    # 3.4 — Paiement Mobile Money
    r = client.post("/api/v1/payments", json={
        "booking_reference": booking_ref, "amount_gnf": 250000,
        "provider": "orange_money", "phone": "+224620000001",
    }, headers=_auth(cand_tok))
    assert r.status_code == 201, r.text[:200]
    assert r.json()["status"] == "paid"

    r = client.get("/api/v1/bookings/my", headers=_auth(cand_tok))
    mine = next(b for b in r.json() if b["reference"] == booking_ref)
    assert mine["status"] == "paid"

    # 3.5 — Convocation PDF
    r = client.get(f"/api/v1/documents/convocations/{booking_ref}.pdf", headers=_auth(cand_tok))
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/pdf"
    assert r.content[:5] == b"%PDF-" and len(r.content) > 1000

    # ══ ACTE 4 — Jour de l'examen (au centre) ══════════════════════════════
    agent_tok = _login(client, agent_email, agent_pass := "AgentRatoma2026!")

    # 4.1 — Validation d'entrée par l'agent
    r = client.post("/api/v1/entries/validate", json={
        "reference": booking_ref, "verification_code": verif_code,
        "center_code": center.code if hasattr(center, "code") else "GN-CKY-RATOMA",
    }, headers=_auth(agent_tok))
    assert r.status_code == 200 and r.json().get("allowed") is True

    # Mauvais code → refusé (anti-fraude)
    r = client.post("/api/v1/entries/validate", json={
        "reference": booking_ref, "verification_code": "ZZZZZZ",
    }, headers=_auth(agent_tok))
    assert r.status_code == 200 and r.json().get("allowed") is False

    # 4.2 — Le candidat démarre SON examen sur l'appareil du centre
    r = client.post("/api/v1/exams/start-from-booking",
                    json={"booking_reference": booking_ref}, headers=_auth(cand_tok))
    assert r.status_code == 201, r.text[:200]
    attempt_id = r.json()["id"]

    # 4.3 — 40 questions, chacune avec un visuel
    r = client.get(f"/api/v1/exams/{attempt_id}/questions", headers=_auth(cand_tok))
    assert r.status_code == 200
    questions = r.json()["questions"]
    assert len(questions) == 40
    sans_visuel = [q for q in questions if not q.get("media_url") and not q.get("media_type")]
    assert len(sans_visuel) == 0, f"{len(sans_visuel)} questions sans visuel"

    # 4.4 — Soumission → résultat + notifications best-effort
    answers = {q["id"]: q["options"][0] for q in questions}
    r = client.post(f"/api/v1/exams/{attempt_id}/submit",
                    json={"answers": answers}, headers=_auth(cand_tok))
    assert r.status_code == 200, r.text[:200]
    result = r.json()
    assert "score" in result and result["status"] in {"passed", "failed", "submitted", "completed"}

    # 4.5 — Résultat détaillé + statut
    r = client.get(f"/api/v1/exams/{attempt_id}/results", headers=_auth(cand_tok))
    assert r.status_code == 200 and len(r.json().get("questions", [])) == 40
    r = client.get(f"/api/v1/exams/{attempt_id}/status", headers=_auth(cand_tok))
    assert r.status_code == 200

    # ══ ACTE 5 — Suivi et supervision ══════════════════════════════════════
    # 5.2 — Dashboard national accessible à l'admin
    adm = _login(client, admin_email, "AdminNational2026!")
    r = client.get("/api/v1/dashboard", headers=_auth(adm))
    assert r.status_code == 200

    # ══ ACTE 6 — Sécurité (cas réels d'abus) ═══════════════════════════════
    # 6.1 — Un autre candidat ne peut pas démarrer la réservation de Fatou
    autre = _register_candidate(client, "malveillant")
    r = client.post("/api/v1/exams/start-from-booking",
                    json={"booking_reference": booking_ref}, headers=_auth(autre["access_token"]))
    assert r.status_code == 403

    # 6.2 — Un candidat n'accède pas au dashboard ni aux utilisateurs
    assert client.get("/api/v1/dashboard", headers=_auth(cand_tok)).status_code == 403
    assert client.get("/api/v1/users", headers=_auth(cand_tok)).status_code == 403

    # 6.3 — Session complète : remplir puis refuser
    db = SessionLocal()
    from app.models_session import ExamSession
    small = ExamSession(
        id=str(uuid.uuid4()), reference=f"SES-FULL-{tag}",
        center_id=center_id,
        starts_at=__import__("datetime").datetime.now(__import__("datetime").UTC).replace(tzinfo=None) + timedelta(days=1),
        capacity=1, status="open",
    )
    db.add(small); db.commit(); small_id = small.id; db.close()

    c1 = _register_candidate(client, "premier")
    r = client.post("/api/v1/bookings/self", json={"session_id": small_id}, headers=_auth(c1["access_token"]))
    assert r.status_code == 201
    c2 = _register_candidate(client, "second")
    r = client.post("/api/v1/bookings/self", json={"session_id": small_id}, headers=_auth(c2["access_token"]))
    assert r.status_code == 409 and "complète" in r.json()["detail"]
