from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db.session import SessionLocal
from app.main import app
from app.models_audit import AuditLog
from app.models_candidate import Candidate


def _admin_headers(client: TestClient) -> dict[str, str]:
    suffix = str(uuid4())[:8]
    email = f"admin-candidate-import-{suffix}@coderoute.gn"
    password = "StrongPass123"
    response = client.post(
        "/api/v1/auth/register",
        json={"email": email, "full_name": "Admin Import Candidat", "password": password, "role": "admin"},
    )
    assert response.status_code == 201
    token_response = client.post("/api/v1/auth/login", data={"username": email, "password": password})
    assert token_response.status_code == 200
    return {"Authorization": f"Bearer {token_response.json()['access_token']}"}


def test_candidate_official_import_requires_admin_authentication() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/candidates/import-official",
            json={
                "source": "Registre officiel",
                "reason": "Import initial",
                "candidates": [
                    {
                        "first_name": "Mamadou",
                        "last_name": "Diallo",
                        "identity_number": "GN-ID-001",
                        "phone": "+224620000001",
                        "permit_category": "B",
                        "status": "registered",
                    }
                ],
            },
        )

    assert response.status_code == 401


def test_admin_can_import_official_candidates_with_audit_log() -> None:
    with TestClient(app) as client:
        suffix = uuid4().hex[:8].upper()
        headers = _admin_headers(client)

        response = client.post(
            "/api/v1/candidates/import-official",
            headers=headers,
            json={
                "source": "Registre national pilote",
                "reason": "Chargement candidats pilotes",
                "candidates": [
                    {
                        "first_name": "Aissatou",
                        "last_name": "Bah",
                        "identity_number": f"GN-CAND-{suffix}",
                        "phone": "+224620000001",
                        "permit_category": "B",
                        "status": "registered",
                    }
                ],
            },
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["imported"] == 1
        assert payload["created"] == 1
        assert payload["updated"] == 0
        candidate_id = payload["candidate_ids"][0]
        reference = payload["references"][0]
        assert reference.startswith("GN-CODE-")

        update_response = client.post(
            "/api/v1/candidates/import-official",
            headers=headers,
            json={
                "source": "Registre national pilote",
                "reason": "Correction telephone",
                "candidates": [
                    {
                        "first_name": "Aissatou",
                        "last_name": "Bah",
                        "identity_number": f"gn-cand-{suffix}",
                        "phone": "+224620000099",
                        "permit_category": "B",
                        "status": "verified",
                    }
                ],
            },
        )

        assert update_response.status_code == 200
        assert update_response.json()["updated"] == 1
        assert update_response.json()["candidate_ids"] == [candidate_id]
        assert update_response.json()["references"] == [reference]

        candidates = client.get("/api/v1/candidates", headers=headers).json()
        imported = next(candidate for candidate in candidates if candidate["id"] == candidate_id)
        assert imported["phone"] == "+224620000099"
        assert imported["status"] == "verified"
        assert imported["identity_number"] == f"GN-CAND-{suffix}"

        with SessionLocal() as db:
            audit_log = db.scalar(
                select(AuditLog)
                .where(AuditLog.action == "candidate.official_import")
                .where(AuditLog.entity == "candidate")
                .order_by(AuditLog.created_at.desc())
            )
            assert audit_log is not None
            assert audit_log.details["source"] == "Registre national pilote"
            assert audit_log.details["imported"] == 1


def test_candidate_official_import_dry_run_does_not_write() -> None:
    with TestClient(app) as client:
        suffix = uuid4().hex[:8].upper()
        identity_number = f"GN-DRY-CAND-{suffix}"
        headers = _admin_headers(client)

        response = client.post(
            "/api/v1/candidates/import-official",
            headers=headers,
            json={
                "source": "Registre national pilote",
                "reason": "Simulation avant chargement",
                "dry_run": True,
                "candidates": [
                    {
                        "first_name": "Mamadou",
                        "last_name": "Barry",
                        "identity_number": identity_number,
                        "phone": "+224620000002",
                        "permit_category": "B",
                        "status": "registered",
                    }
                ],
            },
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["dry_run"] is True
        assert payload["imported"] == 1
        assert payload["created"] == 1
        assert payload["updated"] == 0

        with SessionLocal() as db:
            candidate = db.scalar(select(Candidate).where(Candidate.identity_number == identity_number))
            assert candidate is None


def test_candidate_official_import_rejects_duplicate_identity_numbers() -> None:
    with TestClient(app) as client:
        headers = _admin_headers(client)
        response = client.post(
            "/api/v1/candidates/import-official",
            headers=headers,
            json={
                "source": "Registre national pilote",
                "reason": "Doublon volontaire",
                "candidates": [
                    {
                        "first_name": "Mamadou",
                        "last_name": "Diallo",
                        "identity_number": "GN-DUP-CAND",
                        "phone": "+224620000001",
                        "permit_category": "B",
                        "status": "registered",
                    },
                    {
                        "first_name": "Mamadou",
                        "last_name": "Diallo",
                        "identity_number": "gn-dup-cand",
                        "phone": "+224620000001",
                        "permit_category": "B",
                        "status": "registered",
                    },
                ],
            },
        )

    assert response.status_code == 422
    assert "GN-DUP-CAND" in str(response.json()["detail"])
