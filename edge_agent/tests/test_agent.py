from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import httpx
from fastapi.testclient import TestClient

from coderoute_edge.app import create_app
from coderoute_edge.config import EdgeAgentConfig
from coderoute_edge.crypto import load_or_create_storage_key
from coderoute_edge.media import MediaCache
from coderoute_edge.store import EdgeStore


def _lease_bundle(attempt_id: str | None = None) -> dict:
    attempt_id = attempt_id or str(uuid4())
    lease_id = str(uuid4())
    started = datetime.now(UTC) - timedelta(minutes=1)
    issued = datetime.now(UTC)
    return {
        "lease": {
            "kind": "center_edge_exam_lease_v1",
            "version": 1,
            "lease_id": lease_id,
            "node_id": str(uuid4()),
            "center_id": str(uuid4()),
            "session_id": str(uuid4()),
            "attempt_id": attempt_id,
            "candidate_id": str(uuid4()),
            "issued_at": issued.isoformat().replace("+00:00", "Z"),
            "started_at": started.isoformat().replace("+00:00", "Z"),
            "deadline_at": (started + timedelta(minutes=30)).isoformat().replace("+00:00", "Z"),
            "duration_seconds": 1800,
            "language": "fr",
            "station": {"device_key": "CRG-STATION-EDGE-001"},
            "trace": {"trace_id": str(uuid4()), "question_count": 1, "bank_hash": "a" * 64, "version_label": "test"},
            "questions": [
                {
                    "id": "question-secret-001",
                    "number": 1,
                    "category": "signalisation",
                    "text": "QUESTION CONFIDENTIELLE EDGE TEST",
                    "options": ["Alpha", "Beta"],
                    "media_type": None,
                    "media_url": None,
                    "media_alt": None,
                    "audio_url": None,
                }
            ],
        },
        "lease_hash": "b" * 64,
        "lease_signature_b64": "signed-central-package",
        "signing_key_id": "edge-lease-v1:test",
        "status": "active",
    }


def _config(tmp_path: Path) -> EdgeAgentConfig:
    return EdgeAgentConfig(
        central_url="https://central.test",
        node_id=str(uuid4()),
        center_id=str(uuid4()),
        private_key_path=tmp_path / "private.pem",
        database_path=tmp_path / "edge.db",
        storage_key_path=tmp_path / "storage.key",
        media_cache_dir=tmp_path / "media",
        operator_token="operator-token-that-is-longer-than-32-characters",
        allowed_origins=("https://frontend.test",),
        public_url="https://edge.test:8443",
        allow_insecure_http=True,
    )


def test_store_encrypts_lease_and_journal_and_binds_candidate_station(tmp_path: Path) -> None:
    key = load_or_create_storage_key(tmp_path / "storage.key")
    store = EdgeStore(tmp_path / "edge.db", key)
    bundle = _lease_bundle()
    attempt_id = bundle["lease"]["attempt_id"]

    activation = store.put_lease(bundle, "CRG-STATION-EDGE-001")
    claim = store.claim_candidate_session(
        attempt_id,
        activation["claim_token"],
        "CRG-STATION-EDGE-001",
    )
    access_token = claim["access_token"]
    store.verify_candidate_access(attempt_id, access_token, "CRG-STATION-EDGE-001")

    try:
        store.verify_candidate_access(attempt_id, access_token, "OTHER-STATION")
        raise AssertionError("Un autre poste aurait dû être refusé")
    except PermissionError:
        pass

    event = store.append_answer(attempt_id, "question-secret-001", "Alpha")
    assert event["sequence"] == 1
    assert len(event["event_hash"]) == 64
    assert store.current_answers(attempt_id) == {"question-secret-001": "Alpha"}
    final = store.finalize(attempt_id)
    assert final["journal_head_hash"] == event["event_hash"]
    sync = store.sync_payload(attempt_id)
    assert sync["events"][0]["answer"] == "Alpha"

    raw = b""
    for suffix in ("", "-wal", "-shm"):
        path = Path(str(tmp_path / "edge.db") + suffix)
        if path.exists():
            raw += path.read_bytes()
    assert b"QUESTION CONFIDENTIELLE EDGE TEST" not in raw
    assert b"Alpha" not in raw
    assert activation["claim_token"].encode() not in raw
    assert access_token.encode() not in raw


def test_active_lease_requires_central_revalidation_after_agent_restart(tmp_path: Path) -> None:
    key = load_or_create_storage_key(tmp_path / "storage.key")
    db_path = tmp_path / "edge.db"
    first = EdgeStore(db_path, key)
    bundle = _lease_bundle()
    attempt_id = bundle["lease"]["attempt_id"]
    first.put_lease(bundle, "CRG-STATION-EDGE-002")
    assert first.elapsed_ms(attempt_id) >= 0

    restarted = EdgeStore(db_path, key)
    try:
        restarted.elapsed_ms(attempt_id)
        raise AssertionError("Une tentative active après reboot doit exiger une revalidation centrale")
    except RuntimeError as exc:
        assert "EDGE_REVALIDATION_REQUIRED" in str(exc)


def test_media_prefetch_preserves_signed_lease_and_builds_absolute_lan_projection(tmp_path: Path) -> None:
    body = b"fake-image-content"

    def handler(request: httpx.Request) -> httpx.Response:
        assert str(request.url) == "https://cdn.test/question.jpg"
        return httpx.Response(200, content=body, headers={"content-type": "image/jpeg"})

    http = httpx.Client(transport=httpx.MockTransport(handler))
    cache = MediaCache(
        tmp_path / "media",
        central_url="https://central.test",
        public_url="https://edge.test:8443",
        max_media_bytes=1024 * 1024,
    )
    bundle = _lease_bundle()
    bundle["lease"]["questions"][0]["media_url"] = "https://cdn.test/question.jpg"
    original = json.loads(json.dumps(bundle["lease"]))

    local = cache.prefetch_bundle(bundle, client=http)
    assert local["lease"] == original
    assert local["local_questions"][0]["media_url"].startswith(
        f"https://edge.test:8443/v1/exams/{bundle['lease']['attempt_id']}/media/"
    )
    digest = local["local_questions"][0]["media_url"].rsplit("/", 1)[-1]
    path, content_type = cache.resolve(digest)
    assert path.read_bytes() == body
    assert content_type == "image/jpeg"
    http.close()


class _FakeService:
    def __init__(self, tmp_path: Path):
        self.calls: list[str] = []
        self.media = SimpleNamespace(resolve=lambda digest: (tmp_path / "missing", "image/jpeg"))
        self.store = SimpleNamespace(verify_candidate_access=lambda *args: True, storage_key=b"k" * 32)

    def status(self):
        return {"lease_counts": {"active": 1}}

    def heartbeat(self):
        self.calls.append("heartbeat")
        return {"accepted": True}

    def activate_attempt(self, attempt_id, station_device_key, lang):
        self.calls.append("activate")
        return {
            "attempt_id": attempt_id,
            "lease_id": "lease-1",
            "claim_token": "c" * 43,
            "claim_expires_at": 2_000_000_000,
        }

    def claim_candidate_session(self, attempt_id, claim_token, station_key):
        return {"attempt_id": attempt_id, "lease_id": "lease-1", "access_token": "candidate-token"}

    def sync_attempt(self, attempt_id):
        self.calls.append("sync")
        return {"accepted": True, "attempt_id": attempt_id}

    def candidate_exam(self, attempt_id, access_token, station_key):
        return {"attempt_id": attempt_id, "status": "active", "duration_ms": 1_800_000, "remaining_ms": 1_000_000, "answers": {}, "questions": []}

    def answer(self, *args):
        return {"saved": True, "sequence": 1}

    def finalize(self, *args):
        return {"queued_for_sync": True}


def test_local_api_separates_operator_claim_and_candidate_credentials(tmp_path: Path) -> None:
    config = _config(tmp_path)
    service = _FakeService(tmp_path)
    app = create_app(config=config, service=service)
    with TestClient(app) as client:
        assert client.get("/health").status_code == 200
        assert client.post("/operator/heartbeat").status_code == 401
        ok = client.post(
            "/operator/heartbeat",
            headers={"X-Edge-Operator-Token": config.operator_token},
        )
        assert ok.status_code == 200

        attempt_id = str(uuid4())
        activation = client.post(
            "/operator/leases",
            headers={"X-Edge-Operator-Token": config.operator_token},
            json={"attempt_id": attempt_id, "station_device_key": "CRG-STATION-EDGE-003", "lang": "fr"},
        )
        assert activation.status_code == 200
        assert "access_token" not in activation.json()
        assert "candidate_url" in activation.json()

        claim = client.post(
            "/v1/claim",
            json={
                "attempt_id": attempt_id,
                "claim_token": "c" * 43,
                "station_device_key": "CRG-STATION-EDGE-003",
            },
        )
        assert claim.status_code == 200
        assert claim.json()["access_token"] == "candidate-token"

        assert client.get(f"/v1/exams/{attempt_id}").status_code == 401
        candidate = client.get(
            f"/v1/exams/{attempt_id}",
            headers={
                "X-Edge-Access-Token": "candidate-token",
                "X-CodeRoute-Station-Key": "CRG-STATION-EDGE-003",
            },
        )
        assert candidate.status_code == 200
