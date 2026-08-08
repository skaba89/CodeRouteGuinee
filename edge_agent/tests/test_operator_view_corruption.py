from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

from coderoute_edge.crypto import load_or_create_storage_key
from coderoute_edge.media import MediaCache
from coderoute_edge.operator_view import build_operator_status
from coderoute_edge.store import EdgeStore


def test_corrupt_lease_does_not_hide_other_operator_inventory(tmp_path: Path) -> None:
    key = load_or_create_storage_key(tmp_path / "storage.key")
    store = EdgeStore(tmp_path / "edge.db", key)
    media = MediaCache(
        tmp_path / "media",
        central_url="https://central.test",
        public_url="https://edge.test:8443",
        max_media_bytes=1024 * 1024,
    )
    started = datetime.now(UTC) - timedelta(minutes=1)

    def bundle(attempt_id: str) -> dict:
        return {
            "lease": {
                "lease_id": str(uuid4()),
                "attempt_id": attempt_id,
                "started_at": started.isoformat().replace("+00:00", "Z"),
                "issued_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
                "deadline_at": (started + timedelta(minutes=30)).isoformat().replace("+00:00", "Z"),
                "duration_seconds": 1800,
                "trace": {"question_count": 1},
                "station": {"device_key": "CRG-STATION-OPS-CORRUPT"},
                "questions": [{"id": "q1", "options": ["A", "B"]}],
            },
            "lease_signature_b64": "test",
            "signing_key_id": "test",
        }

    healthy_id = str(uuid4())
    corrupt_id = str(uuid4())
    store.put_lease(bundle(healthy_id), "CRG-STATION-OPS-CORRUPT")
    store.put_lease(bundle(corrupt_id), "CRG-STATION-OPS-CORRUPT")

    with store._connect() as conn:
        conn.execute("UPDATE leases SET ciphertext=? WHERE attempt_id=?", (b"corrupt-ciphertext", corrupt_id))

    result = build_operator_status(store, media)
    assert len(result["leases"]) == 2
    assert result["corrupt_leases"] == 1
    by_id = {item["attempt_id"]: item for item in result["leases"]}
    assert by_id[healthy_id]["runtime_state"] == "ready"
    assert by_id[corrupt_id]["runtime_state"] == "corrupt"
    assert by_id[corrupt_id]["sync_pending"] is False
    assert by_id[corrupt_id]["question_count"] == 0
