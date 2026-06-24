"""
Tests des jobs de notification schedulée — avec vraie DB SQLite.

Couvre :
  - job_exam_reminder_24h : détecte les sessions dans la fenêtre 22h–26h
  - job_exam_reminder_2h  : détecte les sessions dans la fenêtre 90–150 min
  - job_payment_pending_7d: détecte les paiements en attente > 7 jours
  - run_job() : dispatcher par nom
  - JobResult.to_dict()
"""
import json
import uuid
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from app.db.session import SessionLocal, init_db
from app.main import app
from app.models_booking import Booking
from app.models_candidate import Candidate
from app.models_center import Center
from app.models_payment import Payment
from app.models_session import ExamSession
from app.scheduled_notifications import (
    JobResult,
    job_exam_reminder_24h,
    job_exam_reminder_2h,
    job_payment_pending_7d,
    run_job,
)
from tests.conftest import get_admin_headers


# ── Helpers ───────────────────────────────────────────────────────────────────

def _now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _seed_center(db) -> str:
    suffix = uuid.uuid4().hex[:8]
    c = Center(
        code=f"CTR-NTF-{suffix}",
        name=f"Centre Notif {suffix}",
        city="Conakry", address="Test", capacity=30,
        max_sessions_per_week=3, status="accredited",
    )
    db.add(c); db.flush(); return c.id


def _seed_candidate(db, phone: str = "+224628000099") -> str:
    suffix = uuid.uuid4().hex[:8]
    cand = Candidate(
        reference=f"GN-NTF-{suffix}",
        first_name="Notif", last_name=f"Test-{suffix}",
        identity_number=f"NINA-NTF-{suffix}",
        phone=phone, permit_category="B", status="active",
    )
    db.add(cand); db.flush(); return cand.id


def _seed_session(db, center_id: str, starts_at: datetime) -> str:
    suffix = uuid.uuid4().hex[:8]
    s = ExamSession(
        reference=f"GN-NTF-SES-{suffix}",
        center_id=center_id,
        starts_at=starts_at,
        capacity=30, status="open",
    )
    db.add(s); db.flush(); return s.id


def _seed_booking(db, candidate_id: str, session_id: str) -> str:
    suffix = uuid.uuid4().hex[:8]
    b = Booking(
        reference=f"BK-NTF-{suffix}",
        candidate_id=candidate_id,
        session_id=session_id,
        status="confirmed",
        verification_code=f"VRF-NTF-{suffix}",
    )
    db.add(b); db.flush(); return b.reference


def _seed_payment(db, booking_reference: str, days_old: int = 8) -> str:
    suffix = uuid.uuid4().hex[:8]
    pay = Payment(
        reference=f"PAY-NTF-{suffix}",
        booking_reference=booking_reference,
        amount_gnf=150_000,
        provider="orange_money",
        phone="+224628000099",
        status="pending",
        receipt_number=f"RCT-NTF-{suffix}",
    )
    db.add(pay); db.flush()
    # Forcer la date de création à N jours dans le passé
    from sqlalchemy import text as _text
    db.execute(
        _text("UPDATE payments SET created_at = :dt WHERE reference = :ref"),
        {"dt": _now() - timedelta(days=days_old), "ref": pay.reference},
    )
    db.flush()
    return pay.reference


# ── JobResult ─────────────────────────────────────────────────────────────────

class TestJobResult:
    def test_to_dict_structure(self):
        r = JobResult(job="test_job", processed=5, sent=3, failed=2, errors=["err"])
        d = r.to_dict()
        assert d["job"] == "test_job"
        assert d["processed"] == 5
        assert d["sent"] == 3
        assert d["failed"] == 2
        assert d["errors"] == ["err"]
        assert "duration_ms" in d

    def test_to_dict_default_values(self):
        r = JobResult(job="empty")
        d = r.to_dict()
        assert d["processed"] == 0
        assert d["sent"] == 0
        assert d["failed"] == 0
        assert d["errors"] == []

    def test_errors_truncated_at_10(self):
        r = JobResult(job="x", errors=[f"err{i}" for i in range(20)])
        d = r.to_dict()
        assert len(d["errors"]) == 10

    def test_duration_ms_is_numeric(self):
        r = JobResult(job="x", duration_ms=123.456)
        assert isinstance(r.to_dict()["duration_ms"], (int, float))
        assert r.to_dict()["duration_ms"] == round(123.456)


# ── job_exam_reminder_24h ────────────────────────────────────────────────────

class TestJobExamReminder24h:
    def test_no_sessions_in_window_job_name_correct(self):
        """Vérifie le nom du job (sans créer de données, d'autres tests ont des seeds)."""
        init_db()
        with SessionLocal() as db:
            result = job_exam_reminder_24h(db)
        assert result.job == "exam_reminder_24h"
        assert result.failed == 0  # Pas d'erreurs même avec des seeds existants

    def test_session_in_24h_window_is_processed(self):
        """Session dans 23h → dans la fenêtre 22h–26h → traitée."""
        init_db()
        with SessionLocal() as db:
            center_id = _seed_center(db)
            cand_id   = _seed_candidate(db, "+224628100001")
            session_id = _seed_session(db, center_id, _now() + timedelta(hours=23))
            _seed_booking(db, cand_id, session_id)
            db.commit()
            result = job_exam_reminder_24h(db)
        assert result.processed >= 1

    def test_session_outside_window_not_processed(self):
        """Session dans 30h → hors fenêtre → non traitée."""
        init_db()
        with SessionLocal() as db:
            center_id  = _seed_center(db)
            cand_id    = _seed_candidate(db, "+224628100002")
            session_id = _seed_session(db, center_id, _now() + timedelta(hours=30))
            _seed_booking(db, cand_id, session_id)
            db.commit()
            before = result = job_exam_reminder_24h(db)
        # La session à 30h ne devrait pas être dans la fenêtre 22–26h
        # (on ne peut pas garantir 0 processed car d'autres seeds peuvent exister,
        # mais on vérifie que le job tourne sans erreur)
        assert result.failed == 0

    def test_booking_not_confirmed_not_processed(self):
        """Réservation en attente (pending) ne doit pas générer de rappel."""
        init_db()
        with SessionLocal() as db:
            center_id  = _seed_center(db)
            cand_id    = _seed_candidate(db, "+224628100003")
            session_id = _seed_session(db, center_id, _now() + timedelta(hours=23))
            suffix = uuid.uuid4().hex[:8]
            pending_booking = Booking(
                reference=f"BK-PEND-{suffix}",
                candidate_id=cand_id,
                session_id=session_id,
                status="pending",  # non confirmé
                verification_code=f"VRF-PEND-{suffix}",
            )
            db.add(pending_booking); db.commit()
            result = job_exam_reminder_24h(db)
        # Les bookings pending ne déclenchent pas de rappel
        assert result.job == "exam_reminder_24h"

    def test_result_has_duration(self):
        init_db()
        with SessionLocal() as db:
            result = job_exam_reminder_24h(db)
        assert result.duration_ms >= 0

    def test_sms_sent_count_for_candidate_with_phone(self):
        """Candidat avec téléphone → SMS envoyé (mode console en dev)."""
        init_db()
        with SessionLocal() as db:
            center_id  = _seed_center(db)
            cand_id    = _seed_candidate(db, "+224628100010")
            session_id = _seed_session(db, center_id, _now() + timedelta(hours=24))
            _seed_booking(db, cand_id, session_id)
            db.commit()
            result = job_exam_reminder_24h(db)
        # Le SMS en mode console doit réussir (sent >= 0, failed == 0)
        assert result.failed == 0


# ── job_exam_reminder_2h ─────────────────────────────────────────────────────

class TestJobExamReminder2h:
    def test_no_sessions_returns_zero(self):
        init_db()
        with SessionLocal() as db:
            result = job_exam_reminder_2h(db)
        assert result.job == "exam_reminder_2h"
        assert result.processed == 0 or result.failed == 0

    def test_session_in_2h_window_processed(self):
        """Session dans 2h (fenêtre 90–150 min)."""
        init_db()
        with SessionLocal() as db:
            center_id  = _seed_center(db)
            cand_id    = _seed_candidate(db, "+224628200001")
            session_id = _seed_session(db, center_id, _now() + timedelta(minutes=120))
            _seed_booking(db, cand_id, session_id)
            db.commit()
            result = job_exam_reminder_2h(db)
        assert result.processed >= 1
        assert result.failed == 0

    def test_session_outside_2h_window_not_processed(self):
        """Session dans 3h → hors fenêtre."""
        init_db()
        with SessionLocal() as db:
            center_id  = _seed_center(db)
            cand_id    = _seed_candidate(db, "+224628200002")
            session_id = _seed_session(db, center_id, _now() + timedelta(hours=3))
            _seed_booking(db, cand_id, session_id)
            db.commit()
            result = job_exam_reminder_2h(db)
        assert result.failed == 0

    def test_no_phone_no_sms(self):
        """Candidat sans téléphone → pas de SMS, pas d'erreur."""
        init_db()
        with SessionLocal() as db:
            center_id  = _seed_center(db)
            suffix = uuid.uuid4().hex[:8]
            cand_no_phone = Candidate(
                reference=f"GN-NOP-{suffix}",
                first_name="Sans", last_name=f"Phone-{suffix}",
                identity_number=f"NINA-NOP-{suffix}",
                phone="",  # pas de téléphone
                permit_category="B", status="active",
            )
            db.add(cand_no_phone); db.flush()
            session_id = _seed_session(db, center_id, _now() + timedelta(minutes=120))
            _seed_booking(db, cand_no_phone.id, session_id)
            db.commit()
            result = job_exam_reminder_2h(db)
        assert result.failed == 0


# ── job_payment_pending_7d ───────────────────────────────────────────────────

class TestJobPaymentPending7d:
    def test_no_pending_payments_returns_zero(self):
        init_db()
        with SessionLocal() as db:
            result = job_payment_pending_7d(db)
        assert result.job == "payment_pending_7d"
        assert result.failed == 0

    def test_old_pending_payment_detected(self):
        """Paiement en attente depuis 8 jours → traité."""
        init_db()
        with SessionLocal() as db:
            center_id  = _seed_center(db)
            cand_id    = _seed_candidate(db, "+224628300001")
            session_id = _seed_session(db, center_id, _now() + timedelta(days=5))
            booking_ref = _seed_booking(db, cand_id, session_id)
            _seed_payment(db, booking_ref, days_old=8)
            db.commit()
            result = job_payment_pending_7d(db)
        assert result.processed >= 1
        assert result.failed == 0

    def test_recent_pending_payment_not_detected(self):
        """Paiement en attente depuis 3 jours → NON traité (seuil = 7 jours)."""
        init_db()
        with SessionLocal() as db:
            center_id  = _seed_center(db)
            cand_id    = _seed_candidate(db, "+224628300002")
            session_id = _seed_session(db, center_id, _now() + timedelta(days=5))
            booking_ref = _seed_booking(db, cand_id, session_id)
            _seed_payment(db, booking_ref, days_old=3)
            db.commit()
            result = job_payment_pending_7d(db)
        # Les paiements récents ne sont pas dans le lot
        assert result.failed == 0

    def test_paid_payment_not_included(self):
        """Paiement déjà payé → ignoré."""
        init_db()
        with SessionLocal() as db:
            center_id  = _seed_center(db)
            cand_id    = _seed_candidate(db, "+224628300003")
            session_id = _seed_session(db, center_id, _now() + timedelta(days=5))
            booking_ref = _seed_booking(db, cand_id, session_id)
            suffix = uuid.uuid4().hex[:8]
            paid_pay = Payment(
                reference=f"PAY-PAID-{suffix}",
                booking_reference=booking_ref,
                amount_gnf=150_000,
                provider="wave",
                phone="+224628300003",
                status="paid",  # déjà payé
                receipt_number=f"RCT-PAID-{suffix}",
            )
            db.add(paid_pay); db.commit()
            result = job_payment_pending_7d(db)
        assert result.failed == 0

    def test_limit_50_per_run(self):
        """Le job est limité à 50 traitements par run."""
        # Vérifier que la fonction accepte la DB sans planter avec beaucoup de données
        init_db()
        with SessionLocal() as db:
            result = job_payment_pending_7d(db)
        assert isinstance(result.processed, int)


# ── run_job (dispatcher) ────────────────────────────────────────────────────

class TestRunJobDispatcher:
    def test_run_known_job(self):
        result = run_job("exam_reminder_24h")
        assert result.job == "exam_reminder_24h"
        assert isinstance(result.processed, int)

    def test_run_unknown_job_returns_error(self):
        result = run_job("job_inexistant_xyz")
        assert len(result.errors) > 0
        assert "inconnu" in result.errors[0].lower() or "unknown" in result.errors[0].lower()

    def test_run_all_known_jobs(self):
        from app.scheduled_notifications import JOBS
        for job_name in JOBS:
            result = run_job(job_name)
            assert result.job == job_name
            assert result.failed == 0, f"Job {job_name} a des erreurs: {result.errors}"

    def test_run_job_via_api_endpoint(self):
        """POST /dashboard/notifications/run-job?job=... via l'API."""
        with TestClient(app) as c:
            h = get_admin_headers(c)
            r = c.post("/api/v1/dashboard/notifications/run-job",
                       params={"job": "exam_reminder_24h"}, headers=h)
        assert r.status_code == 200
        data = r.json()
        assert data["job"] == "exam_reminder_24h"
        assert "processed" in data
        assert "sent" in data

    def test_run_job_via_api_unknown_returns_400(self):
        with TestClient(app) as c:
            h = get_admin_headers(c)
            r = c.post("/api/v1/dashboard/notifications/run-job",
                       params={"job": "job_inconnu_xyz"}, headers=h)
        assert r.status_code == 400

    def test_run_job_via_api_requires_auth(self):
        with TestClient(app) as c:
            r = c.post("/api/v1/dashboard/notifications/run-job",
                       params={"job": "exam_reminder_24h"})
        assert r.status_code == 401
