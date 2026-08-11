from __future__ import annotations

import threading
import time
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.candidate_creation_rules import (
    assert_candidate_identity_phone_unique,
    build_candidate_reference_locked,
)
from app.db.session import SessionLocal, init_db
from app.main import app
from app.models_candidate import Candidate
from app.routers import candidates, registration


def _candidate_for_reference(reference: str, marker: str) -> Candidate:
    return Candidate(
        reference=reference,
        first_name="Concurrent",
        last_name="Candidate",
        identity_number=f"CONCURRENT-ID-{marker}",
        phone=f"+22462{marker[:7]}",
        permit_category="B",
        status="registered",
    )


def test_all_candidate_creation_routes_use_shared_rules() -> None:
    assert candidates.build_candidate_reference is build_candidate_reference_locked
    assert registration.build_candidate_reference is build_candidate_reference_locked
    assert registration._check_duplicates is assert_candidate_identity_phone_unique


def test_public_registration_rejects_case_insensitive_identity_duplicate() -> None:
    init_db()
    marker = uuid4().hex[:10]
    identity = f"GN-ID-{marker}".upper()
    db = SessionLocal()
    db.add(
        Candidate(
            reference=f"GN-CODE-DUP-{marker}",
            first_name="Existing",
            last_name="Candidate",
            identity_number=identity,
            phone="+224611111111",
            permit_category="B",
            status="registered",
        )
    )
    db.commit()
    db.close()

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/registration/candidate",
            json={
                "first_name": "Nouvelle",
                "last_name": "Candidate",
                "email": f"duplicate-{marker}@coderoute.test",
                "password": "Duplicate123!",
                "phone": "+224622222222",
                "identity_number": identity.lower(),
                "permit_category": "B",
                "city": "Conakry",
            },
        )

    assert response.status_code == 409
    assert "existe déjà" in response.json()["detail"]


def test_postgresql_candidate_reference_lock_serializes_concurrent_creations() -> None:
    init_db()
    probe = SessionLocal()
    dialect = probe.get_bind().dialect.name
    probe.close()
    if dialect != "postgresql":
        pytest.skip("Advisory-lock concurrency contract is PostgreSQL-specific")

    marker = uuid4().hex[:10]
    first_has_lock = threading.Event()
    second_started = threading.Event()
    second_done = threading.Event()
    release_first = threading.Event()
    refs: list[str] = []
    errors: list[BaseException] = []

    def first_worker() -> None:
        db = SessionLocal()
        try:
            reference = build_candidate_reference_locked(db)
            db.add(_candidate_for_reference(reference, f"1{marker}"))
            db.flush()
            refs.append(reference)
            first_has_lock.set()
            if not release_first.wait(timeout=5):
                raise TimeoutError("test did not release first candidate transaction")
            db.commit()
        except BaseException as exc:  # pragma: no cover - asserted in parent thread
            db.rollback()
            errors.append(exc)
            first_has_lock.set()
        finally:
            db.close()

    def second_worker() -> None:
        if not first_has_lock.wait(timeout=5):
            errors.append(TimeoutError("first worker never acquired candidate lock"))
            second_done.set()
            return
        db = SessionLocal()
        try:
            second_started.set()
            reference = build_candidate_reference_locked(db)
            db.add(_candidate_for_reference(reference, f"2{marker}"))
            db.flush()
            refs.append(reference)
            db.commit()
        except BaseException as exc:  # pragma: no cover - asserted in parent thread
            db.rollback()
            errors.append(exc)
        finally:
            db.close()
            second_done.set()

    first = threading.Thread(target=first_worker, daemon=True)
    second = threading.Thread(target=second_worker, daemon=True)
    first.start()
    second.start()

    assert first_has_lock.wait(timeout=5)
    assert second_started.wait(timeout=5)
    # Le second transaction doit rester bloqué tant que le premier advisory
    # lock n'est pas libéré par commit/rollback.
    time.sleep(0.25)
    assert not second_done.is_set()

    release_first.set()
    first.join(timeout=5)
    second.join(timeout=5)

    assert not first.is_alive()
    assert not second.is_alive()
    assert errors == []
    assert len(refs) == 2
    assert len(set(refs)) == 2
