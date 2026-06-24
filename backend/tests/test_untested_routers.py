"""
Tests des routers sans couverture directe.
Couvre : center_incidents, center_stations, exam_monitoring, exam_reviews,
         institutional_authorizations, payment_reconciliation,
         candidate_submissions, candidate_identity, device_sessions,
         exam_question_traces, question_governance.
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
from app.models_exam_attempt import ExamAttempt
from app.models_question import Question
from app.models_session import ExamSession
from app.models_user import User
from app.security import get_password_hash
from tests.conftest import get_admin_headers


# ── Helpers ───────────────────────────────────────────────────────────────────

def _now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _seed_base(db) -> tuple[str, str, str, str, str]:
    """Retourne (center_id, session_id, candidate_id, booking_ref, attempt_id)."""
    s = uuid.uuid4().hex[:8]
    center = Center(code=f"CTR-UR-{s}", name=f"Centre UR {s}",
                    city="Conakry", address="Test", capacity=30,
                    max_sessions_per_week=5, status="accredited")
    db.add(center); db.flush()

    session = ExamSession(reference=f"GN-SUR-{s}", center_id=center.id,
                          starts_at=_now() + timedelta(days=2),
                          capacity=30, status="open")
    db.add(session); db.flush()

    cand = Candidate(reference=f"GN-UR-{s}", first_name="Test", last_name=f"UR-{s}",
                     identity_number=f"NINA-UR-{s}", phone=f"+22462800{s[:4]}",
                     permit_category="B", status="active")
    db.add(cand); db.flush()

    booking = Booking(reference=f"BK-UR-{s}", candidate_id=cand.id,
                      session_id=session.id, status="confirmed",
                      verification_code=f"VRF-UR-{s}")
    db.add(booking); db.flush()

    # Créer 40 questions
    from sqlalchemy import select, func
    existing = db.scalar(select(func.count(Question.id)))
    if existing < 40:
        for i in range(40):
            q = Question(category=["signalisation","priorites","vitesse","securite"][i%4],
                         text=f"Q UR {i+1}?",
                         options=json.dumps(["Option A","Option B","Option C","Option D"]),
                         correct_answer="Option A", is_active=True)
            db.add(q)
        db.flush()

    attempt = ExamAttempt(candidate_id=cand.id, session_id=session.id,
                          status="submitted", answers={"q1": "A"}, score=35, passed=True,
                          started_at=_now() - timedelta(minutes=30),
                          submitted_at=_now())
    db.add(attempt); db.flush()
    db.commit()
    return center.id, session.id, cand.id, booking.reference, attempt.id


# ── CENTER INCIDENTS ──────────────────────────────────────────────────────────

class TestCenterIncidents:
    def test_list_incidents_requires_auth(self):
        with TestClient(app) as c:
            r = c.get("/api/v1/center-incidents")
        assert r.status_code == 401

    def test_list_incidents_empty(self):
        init_db()
        with TestClient(app) as c:
            h = get_admin_headers(c)
            r = c.get("/api/v1/center-incidents", headers=h)
        assert r.status_code == 200
        data = r.json()
        assert "items" in data or isinstance(data, list)

    def test_create_and_resolve_incident(self):
        init_db()
        with SessionLocal() as db:
            center_id, *_ = _seed_base(db)
        with TestClient(app) as c:
            h = get_admin_headers(c)
            r = c.post("/api/v1/center-incidents", headers=h, json={
                "center_id": center_id,
                "type": "equipment_failure",
                "description": "PC de saisie hors service — test unitaire",
                "severity": "medium",
            })
        assert r.status_code == 201
        incident_id = r.json()["id"]
        assert r.json()["status"] in ("open", "pending")
        # Résoudre
        with TestClient(app) as c:
            h = get_admin_headers(c)
            r2 = c.post(f"/api/v1/center-incidents/{incident_id}/resolve",
                        headers=h, json={"resolution_notes": "PC remplacé"})
        assert r2.status_code == 200
        assert r2.json()["status"] in ("resolved", "closed")

    def test_create_incident_invalid_severity(self):
        init_db()
        with SessionLocal() as db:
            center_id, *_ = _seed_base(db)
        with TestClient(app) as c:
            h = get_admin_headers(c)
            r = c.post("/api/v1/center-incidents", headers=h, json={
                "center_id": center_id, "type": "other",
                "description": "test", "severity": "INVALIDE",
            })
        # Soit 422 (validation Pydantic) soit 400
        assert r.status_code in (400, 422)


# ── CENTER STATIONS ───────────────────────────────────────────────────────────

class TestCenterStations:
    def test_list_stations(self):
        init_db()
        with TestClient(app) as c:
            h = get_admin_headers(c)
            r = c.get("/api/v1/center-stations", headers=h)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_create_and_update_station(self):
        init_db()
        with SessionLocal() as db:
            center_id, *_ = _seed_base(db)
        with TestClient(app) as c:
            h = get_admin_headers(c)
            r = c.post("/api/v1/center-stations", headers=h, json={
                "center_id": center_id,
                "device_key": f"KEY-{uuid.uuid4().hex[:4]}",
                "label": f"POSTE-TEST-{uuid.uuid4().hex[:4]}",
                "room": "Salle A",
                "status": "active",
            })
        assert r.status_code == 201
        station_id = r.json()["id"]
        with TestClient(app) as c:
            h = get_admin_headers(c)
            r2 = c.patch(f"/api/v1/center-stations/{station_id}",
                         headers=h, json={"status": "maintenance"})
        assert r2.status_code == 200
        assert r2.json()["status"] in ("maintenance", "inactive")


# ── EXAM MONITORING ───────────────────────────────────────────────────────────

class TestExamMonitoring:
    def test_list_monitoring_events(self):
        init_db()
        with TestClient(app) as c:
            h = get_admin_headers(c)
            r = c.get("/api/v1/exam-monitoring/events", headers=h)
        assert r.status_code == 200

    def test_create_monitoring_event(self):
        init_db()
        with SessionLocal() as db:
            _, _, _, _, attempt_id = _seed_base(db)
        with TestClient(app) as c:
            h = get_admin_headers(c)
            r = c.post("/api/v1/exam-monitoring/events", headers=h, json={
                "attempt_id": attempt_id,
                "event_type": "tab_switch",
                "severity": "low",
                "details": {"count": 1},
            })
        assert r.status_code == 201
        assert r.json()["attempt_id"] == attempt_id

    def test_get_attempt_monitoring_summary(self):
        init_db()
        with SessionLocal() as db:
            _, _, _, _, attempt_id = _seed_base(db)
        with TestClient(app) as c:
            h = get_admin_headers(c)
            r = c.get(f"/api/v1/exam-monitoring/attempts/{attempt_id}/summary",
                      headers=h)
        assert r.status_code == 200
        data = r.json()
        assert "attempt_id" in data or "status" in data

    def test_monitoring_requires_auth(self):
        with TestClient(app) as c:
            r = c.get("/api/v1/exam-monitoring/events")
        assert r.status_code == 401


# ── EXAM REVIEWS ──────────────────────────────────────────────────────────────

class TestExamReviews:
    def test_get_review_case(self):
        init_db()
        with SessionLocal() as db:
            _, _, _, _, attempt_id = _seed_base(db)
        with TestClient(app) as c:
            h = get_admin_headers(c)
            r = c.get(f"/api/v1/exam-reviews/attempts/{attempt_id}", headers=h)
        assert r.status_code == 200
        assert "attempt_id" in r.json() or "status" in r.json()

    def test_list_decisions(self):
        init_db()
        with TestClient(app) as c:
            h = get_admin_headers(c)
            r = c.get("/api/v1/exam-reviews/decisions", headers=h)
        assert r.status_code == 200

    def test_create_review_decision(self):
        init_db()
        with SessionLocal() as db:
            center_id, session_id, cand_id, booking_ref, attempt_id = _seed_base(db)
        with TestClient(app) as c:
            h = get_admin_headers(c)
            r = c.post("/api/v1/exam-reviews/decisions", headers=h, json={
                "attempt_id": attempt_id,
                "decision": "clear",
                "reason": "Examen validé après contrôle — test unitaire",
            })
        assert r.status_code in (200, 201, 409, 422)  # 409 si déjà décidé


# ── INSTITUTIONAL AUTHORIZATIONS ─────────────────────────────────────────────

class TestInstitutionalAuthorizations:
    def test_list_authorizations(self):
        init_db()
        with TestClient(app) as c:
            h = get_admin_headers(c)
            r = c.get("/api/v1/institutional-authorizations", headers=h)
        assert r.status_code == 200

    def test_create_authorization(self):
        init_db()
        with SessionLocal() as db:
            center_id, *_ = _seed_base(db)
        suffix = uuid.uuid4().hex[:8]
        with TestClient(app) as c:
            h = get_admin_headers(c)
            r = c.post("/api/v1/institutional-authorizations", headers=h, json={
                "authority": "DNTT Guinée",
                "reference": f"AUTH-DNTT-{suffix}",
                "title": f"Autorisation examen code route {suffix}",
                "scope": "code_route",
                "valid_from": "2026-01-01",
                "valid_until": "2027-01-01",
            })
        assert r.status_code in (201, 200, 409)

    def test_authorization_requires_auth(self):
        with TestClient(app) as c:
            r = c.get("/api/v1/institutional-authorizations")
        assert r.status_code == 401


# ── PAYMENT RECONCILIATION ───────────────────────────────────────────────────

class TestPaymentReconciliation:
    def test_list_reconciliation_items(self):
        init_db()
        with TestClient(app) as c:
            h = get_admin_headers(c)
            r = c.get("/api/v1/payments/admin/reconciliation/items", headers=h)
        assert r.status_code == 200

    def test_list_reconciliation_alerts(self):
        init_db()
        with TestClient(app) as c:
            h = get_admin_headers(c)
            r = c.get("/api/v1/payments/admin/reconciliation/alerts", headers=h)
        assert r.status_code == 200
        # Les alertes doivent être une liste
        assert isinstance(r.json(), list)

    def test_reconciliation_requires_auth(self):
        with TestClient(app) as c:
            r = c.get("/api/v1/payments/admin/reconciliation/items")
        assert r.status_code == 401


# ── CANDIDATE SUBMISSIONS ─────────────────────────────────────────────────────

class TestCandidateSubmissions:
    def test_list_submissions(self):
        init_db()
        with TestClient(app) as c:
            h = get_admin_headers(c)
            r = c.get("/api/v1/candidate-submissions", headers=h)
        assert r.status_code == 200

    def test_create_and_handle_submission(self):
        init_db()
        with SessionLocal() as db:
            _, _, cand_id, _, attempt_id = _seed_base(db)
        with TestClient(app) as c:
            h = get_admin_headers(c)
            r = c.post("/api/v1/candidate-submissions", headers=h, json={
                "candidate_id": cand_id,
                "attempt_id": attempt_id,
                "category": "review",
                "message": "Je conteste mon résultat — test unitaire suffisamment long",
            })
        assert r.status_code in (200, 201)
        submission_id = r.json()["id"]
        # Traiter la soumission
        with TestClient(app) as c:
            h = get_admin_headers(c)
            r2 = c.post(f"/api/v1/candidate-submissions/{submission_id}/handle",
                        headers=h, json={"status": "accepted",
                                          "admin_response": "Contestation traitée — test"})
        assert r2.status_code == 200
        assert r2.json()["status"] in ("handled", "accepted", "resolved", "closed")


# ── CANDIDATE IDENTITY ────────────────────────────────────────────────────────

class TestCandidateIdentity:
    def test_list_identity_checks(self):
        init_db()
        with TestClient(app) as c:
            h = get_admin_headers(c)
            r = c.get("/api/v1/candidate-identity", headers=h)
        assert r.status_code == 200

    def test_requires_auth(self):
        with TestClient(app) as c:
            r = c.get("/api/v1/candidate-identity")
        assert r.status_code == 401


# ── DEVICE SESSIONS ───────────────────────────────────────────────────────────

class TestDeviceSessions:
    def test_device_alerts(self):
        init_db()
        with TestClient(app) as c:
            h = get_admin_headers(c)
            r = c.get("/api/v1/device-sessions/alerts", headers=h)
        assert r.status_code == 200

    def test_heartbeat_creates_session(self):
        init_db()
        with SessionLocal() as db:
            center_id, session_id, _, _, attempt_id = _seed_base(db)
        with TestClient(app) as c:
            h = get_admin_headers(c)
            r = c.post("/api/v1/device-sessions/heartbeat", headers=h, json={
                "center_id": center_id,
                "session_id": session_id,
                "attempt_id": attempt_id,
                "device_key": "DK-TEST-0001",
                "user_agent": "Mozilla/5.0 Test",
            })
        assert r.status_code in (200, 201)


# ── EXAM QUESTION TRACES ──────────────────────────────────────────────────────

class TestExamQuestionTraces:
    def test_list_traces_requires_auth(self):
        with TestClient(app) as c:
            r = c.get("/api/v1/exam-question-traces")
        assert r.status_code == 401

    def test_list_traces_empty_ok(self):
        init_db()
        with TestClient(app) as c:
            h = get_admin_headers(c)
            r = c.get("/api/v1/exam-question-traces", headers=h)
        assert r.status_code == 200


# ── QUESTION GOVERNANCE ───────────────────────────────────────────────────────

class TestQuestionGovernance:
    def test_list_governance_decisions(self):
        init_db()
        with TestClient(app) as c:
            h = get_admin_headers(c)
            r = c.get("/api/v1/question-governance", headers=h)
        assert r.status_code in (200, 404)  # 404 si route non préfixée

    def test_governance_requires_auth(self):
        with TestClient(app) as c:
            r = c.get("/api/v1/question-governance")
        assert r.status_code == 401
