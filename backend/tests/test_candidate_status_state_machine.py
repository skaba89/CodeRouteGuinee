from __future__ import annotations

from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db.session import SessionLocal, init_db
from app.main import app
from app.models_audit import AuditLog
from app.models_candidate import Candidate
from app.models_user import User
from app.security import create_access_token, get_password_hash


def _headers(user: User) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(user.id, user.role)}"}


def _user(db, marker: str) -> User:
    user = User(
        email=f"status-admin-{marker}@coderoute.test",
        full_name="Status Admin",
        password_hash=get_password_hash("StatusAdmin123!"),
        role="super_admin",
        is_active=True,
    )
    db.add(user)
    db.flush()
    return user


def _candidate(db, marker: str) -> Candidate:
    candidate = Candidate(
        reference=f"GN-CODE-STATUS-{marker}",
        first_name="Mariama",
        last_name="Keita",
        identity_number=f"ID-STATUS-{marker}",
        phone="+224622000099",
        email=f"candidate-status-{marker}@coderoute.test",
        permit_category="B",
        city="Conakry",
        status="registered",
    )
    db.add(candidate)
    db.flush()
    return candidate


def test_candidate_patch_route_is_replaced_once() -> None:
    routes = [
        route
        for route in app.routes
        if getattr(route, "path", None) == "/api/v1/candidates/{candidate_id}"
        and "PATCH" in (getattr(route, "methods", set()) or set())
    ]
    assert len(routes) == 1


def test_generic_patch_cannot_forge_verified_or_arbitrary_status() -> None:
    init_db()
    marker = uuid4().hex[:8]
    db = SessionLocal()
    admin = _user(db, marker)
    candidate = _candidate(db, marker)
    candidate_id = candidate.id
    headers = _headers(admin)
    db.commit()
    db.close()

    with TestClient(app) as client:
        forged_verified = client.patch(
            f"/api/v1/candidates/{candidate_id}",
            headers=headers,
            json={"status": "verified", "status_reason": "Tentative de contournement"},
        )
        assert forged_verified.status_code == 422

        arbitrary = client.patch(
            f"/api/v1/candidates/{candidate_id}",
            headers=headers,
            json={"status": "whatever", "status_reason": "Valeur arbitraire"},
        )
        assert arbitrary.status_code == 422

        missing_reason = client.patch(
            f"/api/v1/candidates/{candidate_id}",
            headers=headers,
            json={"status": "suspended"},
        )
        assert missing_reason.status_code == 422

    db = SessionLocal()
    stored = db.get(Candidate, candidate_id)
    assert stored is not None and stored.status == "registered"
    db.close()


def test_status_changes_are_motivated_audited_and_reactivation_requires_reverification() -> None:
    init_db()
    marker = uuid4().hex[:8]
    db = SessionLocal()
    admin = _user(db, marker)
    candidate = _candidate(db, marker)
    candidate_id = candidate.id
    candidate_ref = candidate.reference
    admin_id = admin.id
    headers = _headers(admin)
    db.commit()
    db.close()

    with TestClient(app) as client:
        suspended = client.patch(
            f"/api/v1/candidates/{candidate_id}",
            headers=headers,
            json={
                "status": "suspended",
                "status_reason": "Suspension administrative de contrôle",
            },
        )
        assert suspended.status_code == 200
        assert suspended.json()["status"] == "suspended"

        # Les autres champs restent éditables sans changer l'état du dossier.
        profile = client.patch(
            f"/api/v1/candidates/{candidate_id}",
            headers=headers,
            json={"city": "Kindia", "phone": "+224623000099"},
        )
        assert profile.status_code == 200
        assert profile.json()["city"] == "Kindia"
        assert profile.json()["status"] == "suspended"

        reactivated = client.patch(
            f"/api/v1/candidates/{candidate_id}",
            headers=headers,
            json={
                "status": "registered",
                "status_reason": "Dossier régularisé, nouvelle vérification requise",
            },
        )
        assert reactivated.status_code == 200
        assert reactivated.json()["status"] == "registered"

        # La validation finale passe obligatoirement par le workflow identité.
        identity = client.post(
            "/api/v1/candidate-identity",
            headers=headers,
            json={
                "candidate_id": candidate_id,
                "document_type": "national_id",
                "document_reference": f"DOC-STATUS-{marker}",
            },
        )
        assert identity.status_code == 201
        decision = client.post(
            f"/api/v1/candidate-identity/{identity.json()['id']}/decision",
            headers=headers,
            json={"status": "verified", "reason": "Document contrôlé et valide"},
        )
        assert decision.status_code == 200

        refreshed = client.get(f"/api/v1/candidates/{candidate_id}", headers=headers)
        assert refreshed.status_code == 200
        assert refreshed.json()["status"] == "verified"

        # Même après une vraie validation, le PATCH générique ne peut pas
        # fabriquer/forcer l'état verified.
        forged_again = client.patch(
            f"/api/v1/candidates/{candidate_id}",
            headers=headers,
            json={"status": "verified", "status_reason": "Ne doit pas passer"},
        )
        assert forged_again.status_code == 422

    db = SessionLocal()
    status_logs = list(
        db.scalars(
            select(AuditLog)
            .where(
                AuditLog.action == "candidate.status_changed",
                AuditLog.entity_id == candidate_id,
            )
            .order_by(AuditLog.created_at.asc())
        ).all()
    )
    assert len(status_logs) == 2
    assert status_logs[0].actor_id == admin_id
    assert status_logs[0].details["candidate_reference"] == candidate_ref
    assert status_logs[0].details["previous_status"] == "registered"
    assert status_logs[0].details["new_status"] == "suspended"
    assert status_logs[0].details["reason"] == "Suspension administrative de contrôle"
    assert status_logs[1].details["previous_status"] == "suspended"
    assert status_logs[1].details["new_status"] == "registered"
    assert "nouvelle vérification" in status_logs[1].details["reason"]

    stored = db.get(Candidate, candidate_id)
    assert stored is not None
    assert stored.status == "verified"
    assert stored.city == "Kindia"
    db.close()
