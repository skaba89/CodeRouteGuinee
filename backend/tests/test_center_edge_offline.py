from __future__ import annotations

import base64
import os
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from fastapi.testclient import TestClient

from app.db.session import SessionLocal, init_db
from app.edge_gateway import canonical_edge_payload, heartbeat_signing_payload, iso_z
from app.edge_offline import (
    JOURNAL_GENESIS_HASH,
    compute_journal_event_hash,
    machine_action_payload,
    verify_answer_journal,
    verify_lease_signature,
)
from app.main import app
from app.models_candidate import Candidate
from app.models_center import Center
from app.models_center_station import CenterStation
from app.models_device_session import DeviceSession
from app.models_exam_attempt import ExamAttempt
from app.models_exam_question_trace import ExamQuestionTrace
from app.models_question import Question
from app.models_session import ExamSession


def _b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _admin_headers(client: TestClient) -> dict[str, str]:
    suffix = uuid4().hex
    email = f"edge-offline-admin-{suffix}@coderoute.local"
    password = "EdgeOfflineAdmin123!"
    register = client.post(
        "/api/v1/auth/register",
        json={"email": email, "full_name": "Admin Edge Offline", "password": password, "role": "admin"},
    )
    assert register.status_code == 201
    login = client.post("/api/v1/auth/login", data={"username": email, "password": password})
    assert login.status_code == 200
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def _sign(private_key: Ed25519PrivateKey, payload: dict) -> str:
    return _b64url(private_key.sign(canonical_edge_payload(payload)))


def _heartbeat_request(
    private_key: Ed25519PrivateKey,
    *,
    node_id: str,
    center_id: str,
    sequence: int,
) -> dict:
    sent_at = datetime.now(UTC).replace(microsecond=0)
    capabilities = ["answer-journal-v1", "exam-lease-v1"]
    signing_payload = heartbeat_signing_payload(
        node_id=node_id,
        center_id=center_id,
        sequence=sequence,
        sent_at=sent_at,
        software_version="edge-0.2.0",
        capabilities=capabilities,
    )
    return {**signing_payload, "signature_b64": _sign(private_key, signing_payload)}


def _machine_request(
    private_key: Ed25519PrivateKey,
    *,
    action: str,
    node_id: str,
    center_id: str,
    sequence: int,
    fields: dict,
) -> tuple[dict, str]:
    sent_at = datetime.now(UTC).replace(microsecond=0)
    signed = machine_action_payload(
        action=action,
        node_id=node_id,
        center_id=center_id,
        sequence=sequence,
        sent_at=iso_z(sent_at),
        fields=fields,
    )
    return signed, _sign(private_key, signed)


def _seed_attempt() -> tuple[Center, ExamAttempt, list[Question], CenterStation]:
    suffix = uuid4().hex[:10].upper()
    center_id = str(uuid4())
    session_id = str(uuid4())
    candidate_id = str(uuid4())
    q1_id = str(uuid4())
    q2_id = str(uuid4())
    attempt_id = str(uuid4())
    trace_id = str(uuid4())
    station_id = str(uuid4())
    device_session_id = str(uuid4())
    device_key = f"CRG-STATION-{suffix}"

    center = Center(
        id=center_id,
        code=f"EDGEOFF-{suffix}",
        name="Centre Edge Offline Pilote",
        city="Conakry",
        address="Centre pilote offline",
        capacity=35,
        status="accredited",
    )
    session = ExamSession(
        id=session_id,
        reference=f"SESSION-EDGE-{suffix}",
        center_id=center_id,
        starts_at=datetime.now(UTC).replace(tzinfo=None),
        capacity=35,
        status="open",
    )
    candidate = Candidate(
        id=candidate_id,
        reference=f"GN-EDGE-{suffix}",
        first_name="Mamadou",
        last_name="Diallo",
        identity_number=f"EDGE-ID-{suffix}",
        phone=f"+22462{suffix[:7]}",
        permit_category="B",
        status="verified",
    )
    q1 = Question(
        id=q1_id,
        category="signalisation",
        text=f"Question Edge A {suffix}",
        options=["A", "B", "C", "D"],
        correct_answer="A",
        explanation="Explication confidentielle A",
        is_active=True,
        validation_status="approved",
    )
    q2 = Question(
        id=q2_id,
        category="priorites",
        text=f"Question Edge B {suffix}",
        options=["A", "B", "C", "D"],
        correct_answer="D",
        explanation="Explication confidentielle B",
        is_active=True,
        validation_status="approved",
    )
    attempt = ExamAttempt(
        id=attempt_id,
        candidate_id=candidate_id,
        session_id=session_id,
        status="started",
        started_at=datetime.now(UTC).replace(tzinfo=None) - timedelta(minutes=2),
    )
    trace = ExamQuestionTrace(
        id=trace_id,
        attempt_id=attempt_id,
        question_ids=[q1_id, q2_id],
        question_count=2,
        bank_hash="b" * 64,
        version_label="edge-offline-test-v1",
        selection_mode="official_test",
    )
    station = CenterStation(
        id=station_id,
        center_id=center_id,
        device_key=device_key,
        label="Poste Edge A",
        status="active",
        room="Salle A",
    )
    device_session = DeviceSession(
        id=device_session_id,
        center_id=center_id,
        session_id=session_id,
        attempt_id=attempt_id,
        device_key=device_key,
        device_label="Poste Edge A",
        status="active",
    )
    with SessionLocal() as db:
        db.add_all([center, session, candidate, q1, q2, attempt, trace, station, device_session])
        db.commit()
        for obj in (center, attempt, q1, q2, station):
            db.refresh(obj)
            db.expunge(obj)
    return center, attempt, [q1, q2], station


def test_edge_offline_lease_and_delayed_sync_scores_centrally() -> None:
    init_db()
    os.environ["EDGE_LEASE_SIGNING_SECRET"] = "edge-offline-test-secret-0123456789-abcdefghijklmnopqrstuvwxyz"
    private_key = Ed25519PrivateKey.generate()
    public_raw = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )

    with TestClient(app) as client:
        headers = _admin_headers(client)
        center, attempt, questions, station = _seed_attempt()

        enroll = client.post(
            "/api/v1/center-edge/nodes",
            headers=headers,
            json={
                "center_id": center.id,
                "label": "Gateway Offline Salle A",
                "public_key_b64": _b64url(public_raw),
                "capabilities": ["exam-lease-v1", "answer-journal-v1"],
            },
        )
        assert enroll.status_code == 201, enroll.text
        node_id = enroll.json()["node_id"]

        heartbeat_1 = _heartbeat_request(private_key, node_id=node_id, center_id=center.id, sequence=1)
        assert client.post("/api/v1/center-edge/heartbeat", json=heartbeat_1).status_code == 200

        issue_fields = {"attempt_id": attempt.id, "lang": "fr"}
        issue_signed, issue_signature = _machine_request(
            private_key,
            action="lease.issue",
            node_id=node_id,
            center_id=center.id,
            sequence=2,
            fields=issue_fields,
        )
        issue = client.post(
            "/api/v1/center-edge/leases/issue",
            json={
                "node_id": node_id,
                "center_id": center.id,
                "sequence": 2,
                "sent_at": issue_signed["sent_at"],
                "attempt_id": attempt.id,
                "lang": "fr",
                "signature_b64": issue_signature,
            },
        )
        assert issue.status_code == 201, issue.text
        lease_response = issue.json()
        lease = lease_response["lease"]
        lease_id = lease["lease_id"]
        assert lease["attempt_id"] == attempt.id
        assert lease["trace"]["question_count"] == 2
        assert lease["station"]["center_station_id"] == station.id
        assert lease["station"]["device_key"] == station.device_key
        assert len(lease["questions"]) == 2
        assert all("correct_answer" not in question for question in lease["questions"])
        assert all("explanation" not in question for question in lease["questions"])

        key = client.get("/api/v1/center-edge/lease-signing-key")
        assert key.status_code == 200
        assert verify_lease_signature(
            lease,
            lease_response["lease_signature_b64"],
            key.json()["public_key_b64"],
        ) is True

        answers = {questions[0].id: "A", questions[1].id: "D"}
        events: list[dict] = []
        prev_hash = JOURNAL_GENESIS_HASH
        for index, (question_id, answer) in enumerate(answers.items(), start=1):
            event_hash = compute_journal_event_hash(
                lease_id=lease_id,
                sequence=index,
                elapsed_ms=index * 5_000,
                question_id=question_id,
                answer=answer,
                prev_hash=prev_hash,
            )
            events.append({
                "sequence": index,
                "elapsed_ms": index * 5_000,
                "question_id": question_id,
                "answer": answer,
                "prev_hash": prev_hash,
                "event_hash": event_hash,
            })
            prev_hash = event_hash

        with SessionLocal() as db:
            stored_attempt = db.get(ExamAttempt, attempt.id)
            assert stored_attempt is not None
            stored_attempt.status = "expired"
            stored_attempt.submitted_at = datetime.now(UTC).replace(tzinfo=None)
            db.add(stored_attempt)
            db.commit()

        heartbeat_3 = _heartbeat_request(private_key, node_id=node_id, center_id=center.id, sequence=3)
        assert client.post("/api/v1/center-edge/heartbeat", json=heartbeat_3).status_code == 200

        finalized_elapsed_ms = 60_000
        sync_fields = {
            "lease_id": lease_id,
            "finalized_elapsed_ms": finalized_elapsed_ms,
            "journal_head_hash": prev_hash,
            "event_count": len(events),
        }
        sync_signed, sync_signature = _machine_request(
            private_key,
            action="lease.offline_sync",
            node_id=node_id,
            center_id=center.id,
            sequence=4,
            fields=sync_fields,
        )
        sync_payload = {
            "node_id": node_id,
            "center_id": center.id,
            "sequence": 4,
            "sent_at": sync_signed["sent_at"],
            **sync_fields,
            "events": events,
            "signature_b64": sync_signature,
        }

        # Un poste désactivé pendant la panne doit bloquer la finalisation automatique.
        with SessionLocal() as db:
            stored_station = db.get(CenterStation, station.id)
            assert stored_station is not None
            stored_station.status = "inactive"
            db.add(stored_station)
            db.commit()
        blocked_sync = client.post("/api/v1/center-edge/offline-sync", json=sync_payload)
        assert blocked_sync.status_code == 409
        assert blocked_sync.json()["detail"]["code"] == "EDGE_STATION_REVOKED_AFTER_LEASE"

        with SessionLocal() as db:
            stored_station = db.get(CenterStation, station.id)
            assert stored_station is not None
            stored_station.status = "active"
            db.add(stored_station)
            db.commit()

        sync = client.post("/api/v1/center-edge/offline-sync", json=sync_payload)
        assert sync.status_code == 200, sync.text
        body = sync.json()
        assert body["accepted"] is True
        assert body["idempotent_replay"] is False
        assert body["status"] == "submitted"
        assert body["score"] == 2
        assert body["passed"] is True

        sync_signed_5, sync_signature_5 = _machine_request(
            private_key,
            action="lease.offline_sync",
            node_id=node_id,
            center_id=center.id,
            sequence=5,
            fields=sync_fields,
        )
        replay = client.post(
            "/api/v1/center-edge/offline-sync",
            json={
                "node_id": node_id,
                "center_id": center.id,
                "sequence": 5,
                "sent_at": sync_signed_5["sent_at"],
                **sync_fields,
                "events": events,
                "signature_b64": sync_signature_5,
            },
        )
        assert replay.status_code == 200, replay.text
        assert replay.json()["idempotent_replay"] is True
        assert replay.json()["score"] == 2


def test_answer_journal_rejects_tampering_and_late_finalization() -> None:
    lease_id = str(uuid4())
    qid = str(uuid4())
    event_hash = compute_journal_event_hash(
        lease_id=lease_id,
        sequence=1,
        elapsed_ms=1_000,
        question_id=qid,
        answer="A",
        prev_hash=JOURNAL_GENESIS_HASH,
    )
    valid_event = {
        "sequence": 1,
        "elapsed_ms": 1_000,
        "question_id": qid,
        "answer": "A",
        "prev_hash": JOURNAL_GENESIS_HASH,
        "event_hash": event_hash,
    }

    proof = verify_answer_journal(
        lease_id=lease_id,
        events=[valid_event],
        allowed_options={qid: {"A", "B"}},
        expected_head_hash=event_hash,
        finalized_elapsed_ms=2_000,
        duration_ms=10_000,
    )
    assert proof["answers"] == {qid: "A"}

    tampered = {**valid_event, "answer": "B"}
    try:
        verify_answer_journal(
            lease_id=lease_id,
            events=[tampered],
            allowed_options={qid: {"A", "B"}},
            expected_head_hash=event_hash,
            finalized_elapsed_ms=2_000,
            duration_ms=10_000,
        )
        raise AssertionError("Le journal altéré aurait dû être rejeté")
    except ValueError as exc:
        assert "Empreinte" in str(exc)

    try:
        verify_answer_journal(
            lease_id=lease_id,
            events=[valid_event],
            allowed_options={qid: {"A", "B"}},
            expected_head_hash=event_hash,
            finalized_elapsed_ms=12_001,
            duration_ms=10_000,
        )
        raise AssertionError("La finalisation hors délai aurait dû être rejetée")
    except ValueError as exc:
        assert "deadline" in str(exc)
