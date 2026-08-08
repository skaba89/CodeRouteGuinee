from __future__ import annotations

import re
import uuid
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit_chain import append_audit
from app.db.session import get_db
from app.edge_gateway import (
    EDGE_AUTHORITY,
    EDGE_HEARTBEAT_MAX_SKEW_SECONDS,
    decode_edge_scope,
    encode_edge_scope,
    iso_z,
    node_is_online,
    verify_edge_signature,
)
from app.edge_offline import (
    EDGE_LEASE_AUTHORITY,
    EDGE_LEASE_SCOPE_KIND,
    decode_lease_scope,
    encode_lease_scope,
    lease_signing_key_id,
    lease_signing_public_key_b64,
    machine_action_payload,
    sign_lease_payload,
    utc_iso,
    verify_answer_journal,
)
from app.exam_engine import (
    EXAM_DURATION_MINUTES,
    build_score_summary,
    build_selected_questions_hash,
    score_answers,
)
from app.models_candidate import Candidate
from app.models_exam_attempt import ExamAttempt
from app.models_exam_question_trace import ExamQuestionTrace
from app.models_institutional_authorization import InstitutionalAuthorization
from app.models_question import Question
from app.models_session import ExamSession
from app.question_i18n import resolve_question_content

# Sous-routeur monté dans `center_edge.router` : pas de préfixe répété ici.
router = APIRouter(tags=["center-edge-offline"])
_HEX64 = re.compile(r"^[0-9a-f]{64}$")


class EdgeLeaseIssueRequest(BaseModel):
    node_id: str
    center_id: str
    sequence: int = Field(ge=1)
    sent_at: datetime
    attempt_id: str
    lang: str = Field(default="fr", min_length=2, max_length=10)
    signature_b64: str = Field(min_length=80, max_length=120)


class EdgeJournalEvent(BaseModel):
    sequence: int = Field(ge=1)
    elapsed_ms: int = Field(ge=0)
    question_id: str
    answer: str = Field(min_length=1, max_length=255)
    prev_hash: str = Field(min_length=64, max_length=64)
    event_hash: str = Field(min_length=64, max_length=64)


class EdgeOfflineSyncRequest(BaseModel):
    node_id: str
    center_id: str
    sequence: int = Field(ge=1)
    sent_at: datetime
    lease_id: str
    finalized_elapsed_ms: int = Field(ge=0)
    journal_head_hash: str = Field(min_length=64, max_length=64)
    events: list[EdgeJournalEvent] = Field(default_factory=list, max_length=1000)
    signature_b64: str = Field(min_length=80, max_length=120)


def _node_authorization(
    db: Session,
    node_id: str,
    *,
    lock: bool = True,
) -> InstitutionalAuthorization | None:
    query = select(InstitutionalAuthorization).where(
        InstitutionalAuthorization.id == node_id,
        InstitutionalAuthorization.authority == EDGE_AUTHORITY,
    )
    if lock:
        query = query.with_for_update()
    return db.scalar(query)


def _verify_node_action(
    db: Session,
    *,
    action: str,
    node_id: str,
    center_id: str,
    sequence: int,
    sent_at: datetime,
    fields: dict,
    signature_b64: str,
    require_recent_heartbeat: bool,
) -> tuple[InstitutionalAuthorization, dict, dict]:
    authorization = _node_authorization(db, node_id, lock=True)
    if not authorization:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Edge node unknown")
    if authorization.status != "active":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Edge node is not active")

    try:
        scope = decode_edge_scope(authorization.scope)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Edge node identity invalid") from exc

    if scope.get("center_id") != center_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Edge node center mismatch")
    if require_recent_heartbeat and not node_is_online(scope):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "EDGE_HEARTBEAT_REQUIRED",
                "message": "Un heartbeat Edge récent est obligatoire avant cette opération.",
            },
        )

    sent_at_aware = sent_at if sent_at.tzinfo else sent_at.replace(tzinfo=UTC)
    sent_at_aware = sent_at_aware.astimezone(UTC)
    now = datetime.now(UTC)
    clock_skew = abs((now - sent_at_aware).total_seconds())
    if clock_skew > EDGE_HEARTBEAT_MAX_SKEW_SECONDS:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "EDGE_CLOCK_SKEW_TOO_HIGH",
                "message": "Horloge Edge hors tolérance.",
                "clock_skew_seconds": round(clock_skew, 3),
            },
        )

    signed_payload = machine_action_payload(
        action=action,
        node_id=node_id,
        center_id=center_id,
        sequence=sequence,
        sent_at=iso_z(sent_at_aware),
        fields=fields,
    )
    if not verify_edge_signature(
        str(scope.get("public_key_b64") or ""),
        signed_payload,
        signature_b64,
    ):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Edge signature")

    last_sequence = int(scope.get("last_sequence") or 0)
    if sequence <= last_sequence:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "EDGE_REQUEST_REPLAY",
                "message": "Requête Edge déjà traitée ou hors séquence.",
                "last_sequence": last_sequence,
                "received_sequence": sequence,
            },
        )

    scope["last_sequence"] = sequence
    scope["last_seen_at"] = now.isoformat().replace("+00:00", "Z")
    scope["last_sent_at"] = sent_at_aware.isoformat().replace("+00:00", "Z")
    authorization.scope = encode_edge_scope(scope)
    authorization.updated_at = now.replace(tzinfo=None)
    db.add(authorization)
    return authorization, scope, signed_payload


def _ordered_trace_questions(db: Session, attempt_id: str) -> tuple[ExamQuestionTrace, list[Question]]:
    trace = db.scalar(select(ExamQuestionTrace).where(ExamQuestionTrace.attempt_id == attempt_id))
    if not trace or not trace.question_ids:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "OFFICIAL_EXAM_TRACE_MISSING", "message": "Trace officielle introuvable."},
        )
    questions = list(db.scalars(select(Question).where(Question.id.in_(trace.question_ids))).all())
    if len(questions) != trace.question_count:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "OFFICIAL_EXAM_TRACE_INCOMPLETE", "message": "Trace officielle incomplète."},
        )
    order = {question_id: index for index, question_id in enumerate(trace.question_ids)}
    questions.sort(key=lambda question: order.get(question.id, 9999))
    return trace, questions


def _lease_authorization(db: Session, lease_id: str, *, lock: bool = False) -> InstitutionalAuthorization | None:
    query = select(InstitutionalAuthorization).where(
        InstitutionalAuthorization.id == lease_id,
        InstitutionalAuthorization.authority == EDGE_LEASE_AUTHORITY,
    )
    if lock:
        query = query.with_for_update()
    return db.scalar(query)


def _existing_attempt_lease(db: Session, attempt_id: str) -> InstitutionalAuthorization | None:
    return db.scalar(select(InstitutionalAuthorization).where(
        InstitutionalAuthorization.authority == EDGE_LEASE_AUTHORITY,
        InstitutionalAuthorization.reference == f"EDGELEASE-{attempt_id}",
    ))


def _public_lease_response(authorization: InstitutionalAuthorization) -> dict:
    try:
        scope = decode_lease_scope(authorization.scope)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return {
        "lease": scope["lease_payload"],
        "lease_hash": scope["lease_hash"],
        "lease_signature_b64": scope["lease_signature_b64"],
        "signing_key_id": scope["signing_key_id"],
        "status": authorization.status,
    }


@router.get("/lease-signing-key")
def get_edge_lease_signing_key() -> dict:
    try:
        return {
            "algorithm": "Ed25519",
            "key_id": lease_signing_key_id(),
            "public_key_b64": lease_signing_public_key_b64(),
        }
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "EDGE_LEASE_SIGNING_NOT_CONFIGURED", "message": str(exc)},
        ) from exc


@router.post("/leases/issue", status_code=status.HTTP_201_CREATED)
def issue_edge_lease(
    payload: EdgeLeaseIssueRequest,
    db: Session = Depends(get_db),
) -> dict:
    lang = payload.lang.strip().lower()
    node_authorization, node_scope, _signed_request = _verify_node_action(
        db,
        action="lease.issue",
        node_id=payload.node_id,
        center_id=payload.center_id,
        sequence=payload.sequence,
        sent_at=payload.sent_at,
        fields={"attempt_id": payload.attempt_id, "lang": lang},
        signature_b64=payload.signature_b64,
        require_recent_heartbeat=True,
    )

    attempt = db.get(ExamAttempt, payload.attempt_id)
    if not attempt:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exam attempt not found")
    if attempt.status != "started":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "EDGE_LEASE_ATTEMPT_NOT_ACTIVE", "message": "La tentative doit être active pour émettre un lease Edge."},
        )

    session = db.get(ExamSession, attempt.session_id)
    if not session or session.center_id != payload.center_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Attempt does not belong to Edge center")

    deadline = attempt.started_at + timedelta(minutes=EXAM_DURATION_MINUTES)
    now_naive = datetime.now(UTC).replace(tzinfo=None)
    if now_naive >= deadline:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "EDGE_LEASE_DEADLINE_PASSED", "message": "La tentative a déjà dépassé sa deadline centrale."},
        )

    existing = _existing_attempt_lease(db, attempt.id)
    if existing:
        existing_scope = decode_lease_scope(existing.scope)
        if existing_scope.get("node_id") != payload.node_id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"code": "EDGE_LEASE_ALREADY_BOUND", "message": "Cette tentative est déjà liée à un autre gateway Edge."},
            )
        db.commit()
        return _public_lease_response(existing)

    trace, questions = _ordered_trace_questions(db, attempt.id)
    candidate = db.get(Candidate, attempt.candidate_id)
    if not candidate:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Candidate not found")

    question_payloads: list[dict] = []
    for index, question in enumerate(questions):
        content = resolve_question_content(question, lang)
        options = content.get("options") if isinstance(content.get("options"), list) else []
        question_payloads.append({
            "id": question.id,
            "number": index + 1,
            "category": question.category,
            "text": content.get("text") or question.text,
            "options": options,
            "media_type": question.media_type,
            "media_url": question.media_url,
            "media_alt": question.media_alt,
            "audio_url": content.get("audio_url"),
        })

    lease_id = str(uuid.uuid4())
    issued_at = datetime.now(UTC)
    lease_payload = {
        "kind": EDGE_LEASE_SCOPE_KIND,
        "version": 1,
        "lease_id": lease_id,
        "node_id": payload.node_id,
        "center_id": payload.center_id,
        "session_id": attempt.session_id,
        "attempt_id": attempt.id,
        "candidate_id": attempt.candidate_id,
        "candidate_reference": candidate.reference,
        "issued_at": utc_iso(issued_at),
        "started_at": utc_iso(attempt.started_at),
        "deadline_at": utc_iso(deadline),
        "duration_seconds": EXAM_DURATION_MINUTES * 60,
        "language": lang,
        "trace": {
            "trace_id": trace.id,
            "question_count": trace.question_count,
            "bank_hash": trace.bank_hash,
            "version_label": trace.version_label,
        },
        "questions": question_payloads,
    }

    try:
        lease_hash, lease_signature_b64, key_id = sign_lease_payload(lease_payload)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "EDGE_LEASE_SIGNING_NOT_CONFIGURED", "message": str(exc)},
        ) from exc

    scope = {
        "kind": EDGE_LEASE_SCOPE_KIND,
        "lease_id": lease_id,
        "node_id": payload.node_id,
        "center_id": payload.center_id,
        "attempt_id": attempt.id,
        "lease_payload": lease_payload,
        "lease_hash": lease_hash,
        "lease_signature_b64": lease_signature_b64,
        "signing_key_id": key_id,
        "server_scoring_snapshot_hash": build_selected_questions_hash(questions),
        "issued_from_node_sequence": payload.sequence,
        "sync_proof": None,
    }
    authorization = InstitutionalAuthorization(
        id=lease_id,
        authority=EDGE_LEASE_AUTHORITY,
        reference=f"EDGELEASE-{attempt.id}",
        title=f"Lease Edge examen {attempt.id}",
        scope=encode_lease_scope(scope),
        status="active",
        valid_from=issued_at.replace(tzinfo=None),
        valid_until=deadline,
    )
    db.add(authorization)
    append_audit(
        db,
        actor_id=None,
        action="center_edge.lease_issued",
        entity="center_edge_exam_lease",
        entity_id=lease_id,
        details={
            "node_id": payload.node_id,
            "center_id": payload.center_id,
            "attempt_id": attempt.id,
            "session_id": attempt.session_id,
            "question_count": trace.question_count,
            "lease_hash": lease_hash,
            "signing_key_id": key_id,
            "node_public_key_fingerprint": node_scope.get("public_key_fingerprint"),
            "deadline_at": utc_iso(deadline),
        },
    )
    db.add(node_authorization)
    db.commit()
    db.refresh(authorization)
    return _public_lease_response(authorization)


@router.post("/offline-sync")
def sync_edge_offline_submission(
    payload: EdgeOfflineSyncRequest,
    db: Session = Depends(get_db),
) -> dict:
    head = payload.journal_head_hash.strip().lower()
    if not _HEX64.fullmatch(head):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="journal_head_hash invalide")

    event_dicts = [event.model_dump() for event in payload.events]
    node_authorization, node_scope, _signed_request = _verify_node_action(
        db,
        action="lease.offline_sync",
        node_id=payload.node_id,
        center_id=payload.center_id,
        sequence=payload.sequence,
        sent_at=payload.sent_at,
        fields={
            "lease_id": payload.lease_id,
            "finalized_elapsed_ms": payload.finalized_elapsed_ms,
            "journal_head_hash": head,
            "event_count": len(event_dicts),
        },
        signature_b64=payload.signature_b64,
        require_recent_heartbeat=True,
    )

    lease_authorization = _lease_authorization(db, payload.lease_id, lock=True)
    if not lease_authorization:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Edge lease not found")
    try:
        lease_scope = decode_lease_scope(lease_authorization.scope)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    if lease_scope.get("node_id") != payload.node_id or lease_scope.get("center_id") != payload.center_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Edge lease ownership mismatch")

    lease_payload = lease_scope.get("lease_payload") or {}
    attempt_id = str(lease_scope.get("attempt_id") or "")
    attempt = db.get(ExamAttempt, attempt_id)
    if not attempt:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exam attempt not found")

    sync_proof = lease_scope.get("sync_proof")
    if lease_authorization.status == "synced" and isinstance(sync_proof, dict):
        if sync_proof.get("journal_head_hash") == head:
            db.commit()
            return {
                "accepted": True,
                "idempotent_replay": True,
                "lease_id": payload.lease_id,
                "attempt_id": attempt.id,
                "status": attempt.status,
                "score": attempt.score,
                "passed": attempt.passed,
                "journal_head_hash": head,
            }
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Lease already synchronized with another journal")

    if attempt.status not in {"started", "expired"}:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "EDGE_ATTEMPT_ALREADY_FINALIZED", "message": "La tentative a déjà été finalisée hors de ce lease Edge."},
        )

    trace, questions = _ordered_trace_questions(db, attempt.id)
    if build_selected_questions_hash(questions) != lease_scope.get("server_scoring_snapshot_hash"):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "EDGE_SCORING_SNAPSHOT_CHANGED",
                "message": "La clé de correction a changé depuis l'émission du lease. Finalisation automatique bloquée.",
            },
        )
    if (lease_payload.get("trace") or {}).get("trace_id") != trace.id:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Lease trace mismatch")

    allowed_options: dict[str, set[str]] = {}
    for question in lease_payload.get("questions") or []:
        question_id = str(question.get("id") or "")
        options = question.get("options") or []
        allowed_options[question_id] = {str(option) for option in options}

    duration_ms = int(lease_payload.get("duration_seconds") or (EXAM_DURATION_MINUTES * 60)) * 1000
    try:
        proof = verify_answer_journal(
            lease_id=payload.lease_id,
            events=event_dicts,
            allowed_options=allowed_options,
            expected_head_hash=head,
            finalized_elapsed_ms=payload.finalized_elapsed_ms,
            duration_ms=duration_ms,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "EDGE_JOURNAL_INVALID", "message": str(exc)},
        ) from exc

    answer_key = {question.id: question.correct_answer for question in questions}
    result = score_answers(answer_key, proof["answers"])
    candidate = db.get(Candidate, attempt.candidate_id)
    summary = build_score_summary(
        result,
        candidate_name=f"{candidate.first_name} {candidate.last_name}" if candidate else "",
    )

    proof_submitted_at = attempt.started_at + timedelta(milliseconds=payload.finalized_elapsed_ms)
    attempt.answers = proof["answers"]
    attempt.score = result["correct_answers"]
    attempt.passed = result["passed"]
    attempt.status = "submitted"
    attempt.submitted_at = proof_submitted_at
    db.add(attempt)
    if candidate and hasattr(candidate, "attempt_count"):
        candidate.attempt_count = (candidate.attempt_count or 0) + 1
        db.add(candidate)

    synced_at = datetime.now(UTC)
    lease_scope["sync_proof"] = {
        "journal_head_hash": proof["journal_head_hash"],
        "event_count": proof["event_count"],
        "finalized_elapsed_ms": payload.finalized_elapsed_ms,
        "proof_submitted_at": utc_iso(proof_submitted_at),
        "synced_at": utc_iso(synced_at),
        "score": result["correct_answers"],
        "passed": result["passed"],
        "node_sequence": payload.sequence,
    }
    lease_authorization.scope = encode_lease_scope(lease_scope)
    lease_authorization.status = "synced"
    lease_authorization.updated_at = synced_at.replace(tzinfo=None)
    db.add(lease_authorization)
    db.add(node_authorization)

    append_audit(
        db,
        actor_id=None,
        action="center_edge.offline_submission_synced",
        entity="exam_attempt",
        entity_id=attempt.id,
        details={
            "lease_id": payload.lease_id,
            "node_id": payload.node_id,
            "center_id": payload.center_id,
            "session_id": attempt.session_id,
            "candidate_id": attempt.candidate_id,
            "event_count": proof["event_count"],
            "journal_head_hash": proof["journal_head_hash"],
            "finalized_elapsed_ms": payload.finalized_elapsed_ms,
            "proof_submitted_at": utc_iso(proof_submitted_at),
            "synced_at": utc_iso(synced_at),
            "score": result["correct_answers"],
            "total": result["total_questions"],
            "passed": result["passed"],
            "unanswered": result["unanswered"],
            "summary": summary,
            "node_public_key_fingerprint": node_scope.get("public_key_fingerprint"),
        },
    )
    db.commit()
    db.refresh(attempt)
    return {
        "accepted": True,
        "idempotent_replay": False,
        "lease_id": payload.lease_id,
        "attempt_id": attempt.id,
        "status": attempt.status,
        "score": attempt.score,
        "passed": attempt.passed,
        "journal_head_hash": proof["journal_head_hash"],
        "proof_submitted_at": utc_iso(proof_submitted_at),
        "synced_at": utc_iso(synced_at),
    }
