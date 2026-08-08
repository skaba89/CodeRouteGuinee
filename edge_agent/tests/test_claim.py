from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

from coderoute_edge.crypto import load_or_create_storage_key
from coderoute_edge.store import EdgeStore


def _bundle() -> dict:
    now = datetime.now(UTC)
    attempt_id = str(uuid4())
    return {
        "lease": {
            "kind": "center_edge_exam_lease_v1",
            "version": 1,
            "lease_id": str(uuid4()),
            "node_id": str(uuid4()),
            "center_id": str(uuid4()),
            "session_id": str(uuid4()),
            "attempt_id": attempt_id,
            "candidate_id": str(uuid4()),
            "issued_at": now.isoformat().replace("+00:00", "Z"),
            "started_at": (now - timedelta(minutes=1)).isoformat().replace("+00:00", "Z"),
            "deadline_at": (now + timedelta(minutes=29)).isoformat().replace("+00:00", "Z"),
            "duration_seconds": 1800,
            "language": "fr",
            "station": {"device_key": "CRG-STATION-CLAIM-001"},
            "trace": {"trace_id": str(uuid4()), "question_count": 0, "bank_hash": "a" * 64, "version_label": "test"},
            "questions": [],
        },
        "lease_hash": "b" * 64,
        "lease_signature_b64": "central-signature",
        "signing_key_id": "edge-lease-v1:test",
        "status": "active",
    }


def test_claim_is_retryable_until_first_authenticated_candidate_call(tmp_path: Path) -> None:
    store = EdgeStore(tmp_path / "edge.db", load_or_create_storage_key(tmp_path / "storage.key"))
    bundle = _bundle()
    attempt_id = bundle["lease"]["attempt_id"]
    activation = store.put_lease(bundle, "CRG-STATION-CLAIM-001")

    assert "access_token" not in activation
    claim_token = activation["claim_token"]

    first = store.claim_candidate_session(attempt_id, claim_token, "CRG-STATION-CLAIM-001")
    retry = store.claim_candidate_session(attempt_id, claim_token, "CRG-STATION-CLAIM-001")
    assert first["access_token"] == retry["access_token"]

    try:
        store.claim_candidate_session(attempt_id, claim_token, "OTHER-STATION")
        raise AssertionError("Un autre poste ne doit jamais pouvoir réclamer la session")
    except PermissionError:
        pass

    store.verify_candidate_access(attempt_id, first["access_token"], "CRG-STATION-CLAIM-001")
    try:
        store.claim_candidate_session(attempt_id, claim_token, "CRG-STATION-CLAIM-001")
        raise AssertionError("Le claim doit être inutilisable après le premier appel authentifié")
    except PermissionError as exc:
        assert "consomm" in str(exc)


def test_claim_expiry_is_enforced(tmp_path: Path) -> None:
    store = EdgeStore(tmp_path / "edge.db", load_or_create_storage_key(tmp_path / "storage.key"))
    bundle = _bundle()
    attempt_id = bundle["lease"]["attempt_id"]
    activation = store.put_lease(bundle, "CRG-STATION-CLAIM-002")

    with store._connect() as conn:
        conn.execute("UPDATE leases SET claim_expires_at=0 WHERE attempt_id=?", (attempt_id,))

    try:
        store.claim_candidate_session(attempt_id, activation["claim_token"], "CRG-STATION-CLAIM-002")
        raise AssertionError("Un claim expiré doit être rejeté")
    except PermissionError as exc:
        assert "expir" in str(exc)
