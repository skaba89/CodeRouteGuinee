from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db.session import SessionLocal, init_db
from app.main import app
from app.models_audit import AuditLog
from app.models_booking import Booking
from app.models_candidate import Candidate
from app.models_center import Center
from app.models_exam_attempt import ExamAttempt
from app.models_session import ExamSession
from app.models_user import User
from app.security import create_access_token, get_password_hash


def _headers(user: User) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(user.id, user.role)}"}


def _user(db, role: str, marker: str, *, center_id: str | None = None) -> User:
    user = User(
        email=f"{role}-{marker}@coderoute.test",
        full_name=f"Test {role} {marker}",
        password_hash=get_password_hash("TestPass123!"),
        role=role,
        is_active=True,
        center_id=center_id,
    )
    db.add(user)
    db.flush()
    return user


def _candidate(db, marker: str, user: User) -> Candidate:
    candidate = Candidate(
        reference=f"GN-CODE-AUTH-{marker}",
        first_name="Mamadou",
        last_name="Diallo",
        identity_number=f"ID-AUTH-{marker}",
        phone=f"+22462{marker[:7]}",
        email=user.email,
        permit_category="B",
        status="registered",
        user_id=user.id,
    )
    db.add(candidate)
    db.flush()
    return candidate


def _center_and_session(db, marker: str) -> tuple[Center, ExamSession]:
    center = Center(
        code=f"CTR-AUTH-{marker}",
        name=f"Centre Auth {marker}",
        city="Conakry",
        commune="Kaloum",
        prefecture="Conakry",
        address="Kaloum",
        capacity=35,
        max_sessions_per_week=3,
        status="accredited",
    )
    db.add(center)
    db.flush()
    session = ExamSession(
        reference=f"GN-SESSION-AUTH-{marker}",
        center_id=center.id,
        starts_at=datetime.now(UTC).replace(tzinfo=None) + timedelta(days=5),
        capacity=35,
        status="planned",
    )
    db.add(session)
    db.flush()
    return center, session


def test_identity_submission_is_scoped_and_candidate_status_tracks_decision() -> None:
    init_db()
    marker = uuid4().hex[:8]
    db = SessionLocal()
    center, session = _center_and_session(db, marker)
    candidate_user_a = _user(db, "candidate", f"a-{marker}")
    candidate_user_b = _user(db, "candidate", f"b-{marker}")
    center_user = _user(db, "center", f"center-{marker}", center_id=center.id)
    admin = _user(db, "super_admin", f"admin-{marker}")
    candidate_a = _candidate(db, f"a-{marker}", candidate_user_a)
    candidate_b = _candidate(db, f"b-{marker}", candidate_user_b)
    db.add(
        Booking(
            reference=f"GN-CONV-AUTH-{marker}",
            candidate_id=candidate_a.id,
            session_id=session.id,
            status="confirmed",
            verification_code=f"VERIFY-AUTH-{marker}",
        )
    )
    ids = {
        "candidate_a": candidate_a.id,
        "candidate_b": candidate_b.id,
        "center_user": center_user.id,
    }
    headers = {
        "candidate_a": _headers(candidate_user_a),
        "center": _headers(center_user),
        "admin": _headers(admin),
    }
    db.commit()
    db.close()

    with TestClient(app) as client:
        other_candidate = client.post(
            "/api/v1/candidate-identity",
            headers=headers["candidate_a"],
            json={
                "candidate_id": ids["candidate_b"],
                "document_type": "national_id",
                "document_reference": f"DOC-B-{marker}",
            },
        )
        assert other_candidate.status_code == 403

        center_out_of_scope = client.post(
            "/api/v1/candidate-identity",
            headers=headers["center"],
            json={
                "candidate_id": ids["candidate_b"],
                "document_type": "national_id",
                "document_reference": f"DOC-B2-{marker}",
            },
        )
        assert center_out_of_scope.status_code == 403

        center_in_scope = client.post(
            "/api/v1/candidate-identity",
            headers=headers["center"],
            json={
                "candidate_id": ids["candidate_a"],
                "document_type": "national_id",
                "document_reference": f"DOC-A-{marker}",
            },
        )
        assert center_in_scope.status_code == 201
        check_id = center_in_scope.json()["id"]

        duplicate_pending = client.post(
            "/api/v1/candidate-identity",
            headers=headers["candidate_a"],
            json={
                "candidate_id": ids["candidate_a"],
                "document_type": "passport",
                "document_reference": f"PASS-A-{marker}",
            },
        )
        assert duplicate_pending.status_code == 409
        assert duplicate_pending.json()["detail"]["code"] == "IDENTITY_CHECK_ALREADY_PENDING"

        verified = client.post(
            f"/api/v1/candidate-identity/{check_id}/decision",
            headers=headers["admin"],
            json={"status": "verified", "reason": "Document authentique"},
        )
        assert verified.status_code == 200
        assert verified.json()["status"] == "verified"

        second = client.post(
            "/api/v1/candidate-identity",
            headers=headers["candidate_a"],
            json={
                "candidate_id": ids["candidate_a"],
                "document_type": "passport",
                "document_reference": f"PASS-A-{marker}",
            },
        )
        assert second.status_code == 201
        second_id = second.json()["id"]

        needs_review = client.post(
            f"/api/v1/candidate-identity/{second_id}/decision",
            headers=headers["admin"],
            json={"status": "needs_review", "reason": "Photo à reprendre"},
        )
        assert needs_review.status_code == 200
        assert needs_review.json()["status"] == "needs_review"

    db = SessionLocal()
    stored_a = db.get(Candidate, ids["candidate_a"])
    stored_b = db.get(Candidate, ids["candidate_b"])
    assert stored_a is not None and stored_a.status == "registered"
    assert stored_b is not None and stored_b.status == "registered"
    submission_audit = db.scalar(
        select(AuditLog)
        .where(
            AuditLog.action == "candidate_identity.submitted",
            AuditLog.entity_id == check_id,
        )
        .limit(1)
    )
    assert submission_audit is not None
    assert submission_audit.actor_id == ids["center_user"]
    db.close()


def test_candidate_appeal_cannot_target_another_user_and_final_decision_is_stable() -> None:
    init_db()
    marker = uuid4().hex[:8]
    db = SessionLocal()
    _center, session = _center_and_session(db, f"appeal-{marker}")
    candidate_user_a = _user(db, "candidate", f"appeal-a-{marker}")
    candidate_user_b = _user(db, "candidate", f"appeal-b-{marker}")
    center_user = _user(db, "center", f"appeal-center-{marker}", center_id=session.center_id)
    admin = _user(db, "super_admin", f"appeal-admin-{marker}")
    candidate_a = _candidate(db, f"appeal-a-{marker}", candidate_user_a)
    candidate_b = _candidate(db, f"appeal-b-{marker}", candidate_user_b)
    attempt_a = ExamAttempt(candidate_id=candidate_a.id, session_id=session.id, status="submitted", score=34, passed=False)
    attempt_b = ExamAttempt(candidate_id=candidate_b.id, session_id=session.id, status="submitted", score=30, passed=False)
    db.add_all([attempt_a, attempt_b])
    db.flush()
    ids = {
        "candidate_a": candidate_a.id,
        "candidate_b": candidate_b.id,
        "attempt_a": attempt_a.id,
        "attempt_b": attempt_b.id,
        "candidate_user_a": candidate_user_a.id,
    }
    headers = {
        "candidate_a": _headers(candidate_user_a),
        "center": _headers(center_user),
        "admin": _headers(admin),
    }
    db.commit()
    db.close()

    with TestClient(app) as client:
        horizontal = client.post(
            "/api/v1/candidate-submissions",
            headers=headers["candidate_a"],
            json={
                "candidate_id": ids["candidate_b"],
                "attempt_id": ids["attempt_b"],
                "category": "exam_result",
                "message": "Je demande une révision de ce résultat.",
            },
        )
        assert horizontal.status_code == 403

        center_cannot_file_candidate_appeal = client.post(
            "/api/v1/candidate-submissions",
            headers=headers["center"],
            json={
                "candidate_id": ids["candidate_a"],
                "attempt_id": ids["attempt_a"],
                "category": "exam_result",
                "message": "Le centre tente de déposer un recours candidat.",
            },
        )
        assert center_cannot_file_candidate_appeal.status_code == 403

        created = client.post(
            "/api/v1/candidate-submissions",
            headers=headers["candidate_a"],
            json={
                "candidate_id": ids["candidate_a"],
                "attempt_id": ids["attempt_a"],
                "category": "exam_result",
                "message": "Je demande une révision de mon résultat d'examen.",
            },
        )
        assert created.status_code == 201
        submission_id = created.json()["id"]
        assert created.json()["category"] == "exam_result"

        duplicate = client.post(
            "/api/v1/candidate-submissions",
            headers=headers["candidate_a"],
            json={
                "candidate_id": ids["candidate_a"],
                "attempt_id": ids["attempt_a"],
                "category": "exam_result",
                "message": "Je tente de déposer le même recours une deuxième fois.",
            },
        )
        assert duplicate.status_code == 409
        assert duplicate.json()["detail"]["code"] == "CANDIDATE_SUBMISSION_ALREADY_OPEN"

        accepted = client.post(
            f"/api/v1/candidate-submissions/{submission_id}/handle",
            headers=headers["admin"],
            json={"status": "accepted", "admin_response": "Recours accepté après contrôle."},
        )
        assert accepted.status_code == 200
        assert accepted.json()["status"] == "accepted"

        conflicting_final = client.post(
            f"/api/v1/candidate-submissions/{submission_id}/handle",
            headers=headers["admin"],
            json={"status": "rejected", "admin_response": "Tentative de décision contradictoire."},
        )
        assert conflicting_final.status_code == 409
        assert conflicting_final.json()["detail"]["code"] == "CANDIDATE_SUBMISSION_ALREADY_FINAL"

        idempotent_final = client.post(
            f"/api/v1/candidate-submissions/{submission_id}/handle",
            headers=headers["admin"],
            json={"status": "accepted", "admin_response": "Même décision répétée."},
        )
        assert idempotent_final.status_code == 200
        assert idempotent_final.json()["status"] == "accepted"

    db = SessionLocal()
    audit = db.scalar(
        select(AuditLog)
        .where(
            AuditLog.action == "candidate_submission.created",
            AuditLog.entity_id == submission_id,
        )
        .limit(1)
    )
    assert audit is not None
    assert audit.actor_id == ids["candidate_user_a"]
    db.close()
