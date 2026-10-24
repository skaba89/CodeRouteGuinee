"""Surveillance statistique des centres (taux anormal, éloignement, hors créneau)."""
from __future__ import annotations

from datetime import datetime, timedelta
from uuid import uuid4

from fastapi.testclient import TestClient

from app.center_anomalies import detect_center_anomalies
from app.db.session import SessionLocal, init_db
from app.main import app
from app.models_candidate import Candidate
from app.models_center import Center
from app.models_exam_attempt import ExamAttempt
from app.models_session import ExamSession
from tests.conftest import get_admin_headers, get_auth_headers


# Chaque test travaille sur une année isolée : aucune autre donnée n'y figure.
def _period(year: int) -> dict:
    return {"since": datetime(year, 1, 1), "until": datetime(year + 1, 1, 1)}


def _center_with_history(db, *, year: int, prefecture: str, candidate_city: str, exams: int, passed: int,
                         off_slot: int = 0) -> Center:
    suffix = uuid4().hex[:8]
    center = Center(code=f"ANOM-{suffix}", name=f"Centre {prefecture} {suffix}", city=prefecture,
                    prefecture=prefecture, address="—", status="accredited")
    db.add(center)
    db.flush()
    starts_at = datetime(year, 6, 1, 9, 0)
    session = ExamSession(reference=f"ANOM-SES-{suffix}", center_id=center.id, starts_at=starts_at,
                          capacity=exams, status="closed")
    db.add(session)
    db.flush()
    for index in range(exams):
        candidate = Candidate(reference=f"ANOM-{suffix}-{index}", first_name="Test", last_name="Anomalie",
                              identity_number=f"ANOM-{suffix}-{index}", phone="+224620000000",
                              city=candidate_city, status="verified")
        db.add(candidate)
        db.flush()
        started = starts_at + timedelta(minutes=120 if index < off_slot else 5)
        db.add(ExamAttempt(candidate_id=candidate.id, session_id=session.id, status="submitted",
                           score=38 if index < passed else 25, passed=index < passed,
                           started_at=started, submitted_at=started + timedelta(minutes=20)))
    db.commit()
    return center


def _flagged(report: dict, center: Center) -> dict | None:
    return next((row for row in report["centers"] if row["center_id"] == center.id), None)


def test_atypical_center_is_flagged_and_typical_one_is_not() -> None:
    init_db()
    with SessionLocal() as db:
        normal = [_center_with_history(db, year=2001, prefecture="Kindia", candidate_city="Kindia", exams=40, passed=24)
                  for _ in range(4)]
        atypical = _center_with_history(db, year=2001, prefecture="Siguiri", candidate_city="Conakry",
                                        exams=40, passed=40, off_slot=2)
        report = detect_center_anomalies(db, **_period(2001))

    row = _flagged(report, atypical)
    assert row is not None
    assert {alert["code"] for alert in row["alerts"]} == {
        "PASS_RATE_OUTLIER", "REMOTE_CANDIDATES", "OFF_SLOT_ATTEMPTS",
    }
    assert row["region"] == "Kankan"
    assert row["off_slot_attempts"] == 2
    assert row["remote_share_pct"] == 100.0
    assert all(_flagged(report, center) is None for center in normal)
    assert report["national"]["exams"] == 200


def test_small_volume_is_not_judged_on_pass_rate() -> None:
    init_db()
    with SessionLocal() as db:
        _center_with_history(db, year=2003, prefecture="Kindia", candidate_city="Kindia", exams=60, passed=30)
        tiny = _center_with_history(db, year=2003, prefecture="Labé", candidate_city="Labé", exams=5, passed=5)
        report = detect_center_anomalies(db, **_period(2003))
    assert _flagged(report, tiny) is None


def test_center_anomalies_endpoint_is_reserved_to_national_administration() -> None:
    init_db()
    with TestClient(app) as client:
        assert client.get("/api/v1/dashboard/center-anomalies", headers=get_admin_headers(client)).status_code == 200
        assert client.get("/api/v1/dashboard/center-anomalies",
                          headers=get_auth_headers(client, "center")).status_code == 403
        assert client.get("/api/v1/dashboard/center-anomalies",
                          headers=get_auth_headers(client, "candidate")).status_code == 403
