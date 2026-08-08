from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

from coderoute_edge.crypto import load_or_create_storage_key
from coderoute_edge.media import MediaCache
from coderoute_edge.operator_view import build_operator_status
from coderoute_edge.store import EdgeStore


def _bundle(attempt_id: str) -> dict:
    started = datetime.now(UTC) - timedelta(minutes=2)
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
            "issued_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            "started_at": started.isoformat().replace("+00:00", "Z"),
            "deadline_at": (started + timedelta(minutes=30)).isoformat().replace("+00:00", "Z"),
            "duration_seconds": 1800,
            "language": "fr",
            "station": {
                "center_station_id": str(uuid4()),
                "device_key": "CRG-STATION-OPS-001",
                "label": "Poste 01",
                "room": "Salle A",
            },
            "trace": {"trace_id": str(uuid4()), "question_count": 1, "bank_hash": "a" * 64, "version_label": "test"},
            "questions": [{
                "id": "question-secret-ops-001",
                "number": 1,
                "category": "signalisation",
                "text": "QUESTION ULTRA CONFIDENTIELLE OPERATEUR",
                "options": ["Réponse secrète A", "Réponse secrète B"],
                "media_type": None,
                "media_url": None,
                "media_alt": None,
                "audio_url": None,
            }],
        },
        "lease_hash": "b" * 64,
        "lease_signature_b64": "signature-test",
        "signing_key_id": "edge-lease-v1:test",
        "status": "active",
    }


def test_operator_view_is_sanitized_and_tracks_sync_state(tmp_path: Path) -> None:
    key = load_or_create_storage_key(tmp_path / "storage.key")
    store = EdgeStore(tmp_path / "edge.db", key)
    media = MediaCache(
        tmp_path / "media",
        central_url="https://central.test",
        public_url="https://edge.test:8443",
        max_media_bytes=1024 * 1024,
    )
    attempt_id = str(uuid4())
    bundle = _bundle(attempt_id)
    activation = store.put_lease(bundle, "CRG-STATION-OPS-001")

    initial = build_operator_status(store, media)
    assert initial["lease_counts"] == {"active": 1}
    assert initial["sync_pending"] == 0
    assert initial["revalidation_required"] == 0
    item = initial["leases"][0]
    assert item["attempt_id"] == attempt_id
    assert item["station"]["label"] == "Poste 01"
    assert item["question_count"] == 1
    assert item["event_count"] == 0
    assert item["claim_state"] == "pending"

    serialized = json.dumps(initial, ensure_ascii=False)
    assert "QUESTION ULTRA CONFIDENTIELLE OPERATEUR" not in serialized
    assert "Réponse secrète A" not in serialized
    assert activation["claim_token"] not in serialized
    assert "access_token" not in serialized
    assert "ciphertext" not in serialized
    assert "station_key_hash" not in serialized

    claim = store.claim_candidate_session(attempt_id, activation["claim_token"], "CRG-STATION-OPS-001")
    store.verify_candidate_access(attempt_id, claim["access_token"], "CRG-STATION-OPS-001")
    store.append_answer(attempt_id, "question-secret-ops-001", "Réponse secrète A")
    store.finalize(attempt_id)

    finalized = build_operator_status(store, media)
    assert finalized["sync_pending"] == 1
    item = finalized["leases"][0]
    assert item["status"] == "finalized"
    assert item["event_count"] == 1
    assert item["claim_state"] == "claimed"

    serialized = json.dumps(finalized, ensure_ascii=False)
    assert "Réponse secrète A" not in serialized
    assert claim["access_token"] not in serialized

    store.mark_synced(attempt_id)
    synced = build_operator_status(store, media)
    assert synced["sync_pending"] == 0
    assert synced["leases"][0]["status"] == "synced"


def test_operator_view_flags_active_lease_after_restart(tmp_path: Path) -> None:
    key = load_or_create_storage_key(tmp_path / "storage.key")
    db_path = tmp_path / "edge.db"
    first = EdgeStore(db_path, key)
    attempt_id = str(uuid4())
    first.put_lease(_bundle(attempt_id), "CRG-STATION-OPS-001")

    restarted = EdgeStore(db_path, key)
    media = MediaCache(
        tmp_path / "media",
        central_url="https://central.test",
        public_url="https://edge.test:8443",
        max_media_bytes=1024 * 1024,
    )
    status = build_operator_status(restarted, media)
    assert status["revalidation_required"] == 1
    assert status["leases"][0]["runtime_state"] == "revalidation_required"
