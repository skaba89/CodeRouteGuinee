"""Démonstration DNTT : le seed produit un environnement où le parcours complet passe.

Rejoue, avec les comptes de démonstration, exactement le parcours montré :
inscription publique → identité → réservation de la session live → paiement
Mobile Money → convocation PDF → contrôle d'entrée par le chef de centre de
Kaloum → examen illustré → résultat.
"""
from __future__ import annotations

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db.session import SessionLocal, init_db
from app.main import app
from app.models_candidate import Candidate
from app.models_center import Center
from app.models_exam_question_trace import ExamQuestionTrace
from app.models_question import Question
from app.models_user import User
from app.official_media_readiness import runtime_ready_official_questions
from app.seed_full import (
    SEED_PASSWORD,
    assign_center_users,
    seed_candidates_and_flows,
    seed_centers,
    seed_questions,
    seed_sessions,
    seed_users,
)


@pytest.fixture
def demo_env():
    """Seed de démonstration réduit (activité nationale sur 4 centres)."""
    from app.seed_demo_dntt import (
        apply_demo_media,
        create_live_session,
        seed_demo_accounts,
        seed_national_activity,
        verify_seeded_candidates,
    )

    init_db()
    with SessionLocal() as db:
        users = seed_users(db)
        centers = seed_centers(db)
        assign_center_users(db, users, centers)
        questions = seed_questions(db)
        sessions = seed_sessions(db, centers)
        admin = users["super_admin@coderoute.gov.gn"]
        seed_candidates_and_flows(db, sessions, questions, admin)
        accounts = seed_demo_accounts(db)
        apply_demo_media(db)
        verify_seeded_candidates(db, admin)
        seed_national_activity(
            db, admin, accounts["auto-ecole.kaloum@coderoute.gov.gn"], scale=0.3, center_limit=4,
        )
        live = create_live_session(db, 5)
        yield {"live_session_id": live.id}


def _login(client: TestClient, email: str, password: str = SEED_PASSWORD) -> dict[str, str]:
    response = client.post("/api/v1/auth/login", data={"username": email, "password": password})
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_demo_accounts_cover_every_role(demo_env) -> None:
    with SessionLocal() as db:
        roles = {
            u.role
            for u in db.scalars(select(User).where(User.email.like("%coderoute.gov.gn") | User.email.like("%@demo.coderoute.gn"))).all()
        }
        chef = db.scalar(select(User).where(User.email == "chef.conakry@coderoute.gov.gn"))
        kaloum = db.scalar(select(Center).where(Center.code == "CRG-KAL-001"))
        mamadou = db.scalar(select(Candidate).where(Candidate.reference == "GN-CAND-2026-001"))
        mamadou_user = db.scalar(select(User).where(User.email == "mamadou.diallo@demo.coderoute.gn"))

    assert {"super_admin", "admin", "center", "driving_school", "candidate"} <= roles
    # Sans rattachement, le chef de centre serait refusé au contrôle d'entrée.
    assert chef.center_id == kaloum.id
    assert mamadou.user_id == mamadou_user.id


def test_seed_full_scenarios_match_their_declared_outcome(demo_env) -> None:
    """Régression : les scénarios `admitted`/`paid_future` étaient ignorés et les scores faux."""
    from app.models_exam_attempt import ExamAttempt
    from app.models_payment import Payment
    from app.models_session import ExamSession
    from app.seed_full import CANDIDATES_DATA

    with SessionLocal() as db:
        for spec in CANDIDATES_DATA:
            ref = spec["reference"]
            candidate = db.scalar(select(Candidate).where(Candidate.reference == ref))
            attempt = db.scalar(select(ExamAttempt).where(ExamAttempt.candidate_id == candidate.id))
            paid = db.scalar(select(Payment).where(
                Payment.booking_reference == f"GN-BOOK-{ref}", Payment.status == "paid",
            ))
            if spec["scenario"] in ("admitted", "failed"):
                assert attempt is not None, ref
                assert attempt.score == spec["score"], ref
                assert attempt.passed is (spec["scenario"] == "admitted"), ref
                assert db.get(ExamSession, attempt.session_id).starts_at < attempt.submitted_at, ref
            else:
                assert attempt is None, ref
            assert (paid is not None) == (spec["scenario"] in ("admitted", "failed", "paid_future")), ref

    with TestClient(app) as client:
        certificate = client.get("/api/v1/exams/ATT-GN-CAND-2026-001/certificate/verify")
    assert certificate.status_code == 200
    assert certificate.json()["valid"] is True and certificate.json()["score"] == 38


def test_demo_bank_passes_the_exam_media_gate(demo_env) -> None:
    with SessionLocal() as db:
        approved = list(db.scalars(
            select(Question).where(Question.is_active.is_(True), Question.validation_status == "approved")
        ).all())
        eligible, _ = runtime_ready_official_questions(db, approved)
    assert len(eligible) >= 40
    assert all(q.media_url.startswith("https://") and q.media_alt for q in eligible)


def test_demo_media_refuses_non_https_base(monkeypatch) -> None:
    from app.seed_demo_dntt import _media_base_url

    monkeypatch.setenv("DEMO_MEDIA_BASE_URL", "http://localhost:5173/media/")
    with pytest.raises(RuntimeError, match="HTTPS"):
        _media_base_url()


def test_demo_seed_is_blocked_outside_development(monkeypatch) -> None:
    from app.seed_demo_dntt import run

    monkeypatch.delenv("ALLOW_DEMO_SEED_NON_DEV", raising=False)
    with pytest.raises(RuntimeError, match="Seed bloqué"):
        run(live_in=15, live_only=True, scale=1.0)


def test_full_candidate_journey_on_demo_environment(demo_env) -> None:
    suffix = uuid4().hex[:8]
    with TestClient(app) as client:
        admin = _login(client, "admin.national@coderoute.gov.gn")
        chef = _login(client, "chef.conakry@coderoute.gov.gn")

        registration = client.post("/api/v1/registration/candidate", json={
            "first_name": "Aïssatou", "last_name": "Barry",
            "identity_number": f"GN-CNI-{suffix}", "phone": f"+224621{uuid4().int % 10**6:06d}",
            "permit_category": "B", "city": "Conakry",
            "email": f"aissatou.{suffix}@demo.coderoute.gn", "password": "Candidat2026!",
        })
        assert registration.status_code == 201, registration.text
        reg = registration.json()
        candidate = {"Authorization": f"Bearer {reg['access_token']}"}

        identity = client.post("/api/v1/candidate-identity", headers=admin, json={
            "candidate_id": reg["candidate_id"], "document_type": "national_id",
            "document_reference": f"CNI-{suffix}",
        })
        assert identity.status_code == 201, identity.text
        decision = client.post(f"/api/v1/candidate-identity/{identity.json()['id']}/decision",
                               headers=admin, json={"status": "verified", "reason": "CNI contrôlée"})
        assert decision.status_code == 200, decision.text

        booking = client.post("/api/v1/bookings/self", headers=candidate,
                              json={"session_id": demo_env["live_session_id"]})
        assert booking.status_code == 201, booking.text
        booking = booking.json()

        payment = client.post("/api/v1/payments", headers=candidate, json={
            "booking_reference": booking["reference"], "amount_gnf": 150000,
            "provider": "orange_money", "phone": "+224622000111",
        })
        assert payment.status_code == 201, payment.text
        assert payment.json()["status"] == "paid"

        pdf = client.get(f"/api/v1/documents/convocations/{booking['reference']}.pdf", headers=candidate)
        assert pdf.status_code == 200, pdf.text
        assert pdf.content.startswith(b"%PDF")

        entry = client.post("/api/v1/entries/validate", headers=chef, json={
            "reference": booking["reference"], "verification_code": booking["verification_code"],
            "center_code": "CRG-KAL-001",
        })
        assert entry.status_code == 200, entry.text
        assert entry.json()["allowed"] is True, entry.json()

        start = client.post("/api/v1/exams/start-from-booking", headers=candidate,
                            json={"booking_reference": booking["reference"]})
        assert start.status_code == 201, start.text
        attempt = start.json()

        questions = client.get(f"/api/v1/exams/{attempt['id']}/questions", headers=candidate)
        assert questions.status_code == 200, questions.text
        items = questions.json().get("questions") or questions.json().get("items")
        assert len(items) == 40
        assert all(q["media_url"].startswith("https://") for q in items)

        with SessionLocal() as db:
            trace = db.scalar(select(ExamQuestionTrace).where(ExamQuestionTrace.attempt_id == attempt["id"]))
            key = {q.id: q.correct_answer for q in db.scalars(
                select(Question).where(Question.id.in_(trace.question_ids))
            ).all()}
        submit = client.post(f"/api/v1/exams/{attempt['id']}/submit", headers=candidate,
                             json={"answers": {qid: key[qid] for qid in trace.question_ids}})
        assert submit.status_code == 200, submit.text
        assert submit.json()["passed"] is True

        results = client.get(f"/api/v1/exams/{attempt['id']}/results", headers=candidate)
        assert results.status_code == 200, results.text
        certificate = client.get(f"/api/v1/exams/{attempt['id']}/certificate/verify")
        assert certificate.status_code == 200 and certificate.json()["valid"] is True
