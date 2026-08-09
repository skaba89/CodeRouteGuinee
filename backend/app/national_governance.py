"""P12 — gouvernance nationale et homologation DNTT.

Les politiques et dossiers sont stockés dans InstitutionalAuthorization afin de
ne pas introduire de migration DB pendant la phase d'homologation. Le champ
`scope` contient un document JSON canonique versionné ; `reference` reste la
clé institutionnelle stable.

Important : une politique approuvée n'altère jamais silencieusement le moteur
d'examen. Son activation exige un alignement exact avec la configuration
technique courante. Une évolution réglementaire se fait donc en deux temps :
1. approbation de la politique ; 2. adaptation/test du runtime ; 3. activation.
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import HTTPException, status
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.exam_engine import (
    CATEGORY_DISTRIBUTION,
    EXAM_DURATION_MINUTES,
    EXAM_PASS_THRESHOLD,
    EXAM_QUESTIONS_TOTAL,
    filter_official_exam_pool,
)
from app.models_audit import AuditLog
from app.models_center import Center
from app.models_institutional_authorization import InstitutionalAuthorization
from app.models_question import Question
from app.models_user import User

POLICY_KIND = "coderoute_national_exam_policy_v1"
DOSSIER_KIND = "coderoute_national_homologation_dossier_v1"
MANDATORY_EVIDENCE = {
    "dntt_exam_rules",
    "legal_review",
    "security_assessment",
    "operations_readiness",
    "content_signoff",
}

_CODE_RE = re.compile(r"^[A-Z0-9][A-Z0-9_-]{2,39}$")
_VERSION_RE = re.compile(r"^[0-9]{4}(?:\.[0-9]{1,3}){1,2}$")


def _now() -> datetime:
    return datetime.now(UTC)


def _naive(value: datetime | None = None) -> datetime:
    current = value or _now()
    return current.astimezone(UTC).replace(tzinfo=None)


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), default=str)


def document_sha256(value: dict) -> str:
    material = {k: v for k, v in value.items() if k != "document_sha256"}
    return hashlib.sha256(_canonical(material).encode("utf-8")).hexdigest()


def _dump(document: dict) -> str:
    document = dict(document)
    document["document_sha256"] = document_sha256(document)
    return _canonical(document)


def _load(record: InstitutionalAuthorization) -> dict:
    try:
        document = json.loads(record.scope)
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Document institutionnel illisible") from exc
    expected = str(document.get("document_sha256", ""))
    if not expected or not hashlib.sha256(
        _canonical({k: v for k, v in document.items() if k != "document_sha256"}).encode("utf-8")
    ).hexdigest() == expected:
        raise HTTPException(
            status_code=409,
            detail={"code": "INSTITUTIONAL_DOCUMENT_HASH_MISMATCH", "reference": record.reference},
        )
    return document


class LegalReference(BaseModel):
    reference: str = Field(min_length=3, max_length=160)
    title: str = Field(min_length=3, max_length=255)
    issued_on: str | None = Field(default=None, max_length=32)
    source_ref: str | None = Field(default=None, max_length=255)


class ExamPolicyParameters(BaseModel):
    question_count: int = Field(ge=10, le=100)
    pass_threshold: int = Field(ge=1, le=100)
    duration_minutes: int = Field(ge=5, le=180)
    category_distribution: dict[str, int]
    one_attempt_per_session: bool = True
    retake_cooldown_hours: int = Field(default=0, ge=0, le=24 * 365)

    @model_validator(mode="after")
    def validate_contract(self):
        if self.pass_threshold > self.question_count:
            raise ValueError("pass_threshold ne peut pas dépasser question_count")
        if not self.category_distribution:
            raise ValueError("category_distribution est obligatoire")
        if any(not key.strip() or value < 0 for key, value in self.category_distribution.items()):
            raise ValueError("category_distribution contient une valeur invalide")
        if sum(self.category_distribution.values()) != self.question_count:
            raise ValueError("la somme category_distribution doit égaler question_count")
        return self


class PolicyCreate(BaseModel):
    code: str
    version: str
    title: str = Field(min_length=5, max_length=255)
    authority: str = Field(default="DNTT", min_length=2, max_length=180)
    parameters: ExamPolicyParameters
    legal_references: list[LegalReference] = Field(min_length=1)
    rationale: str = Field(min_length=10, max_length=4000)

    @model_validator(mode="after")
    def validate_identity(self):
        self.code = self.code.strip().upper()
        self.version = self.version.strip()
        if not _CODE_RE.fullmatch(self.code):
            raise ValueError("code doit être institutionnel (A-Z, 0-9, _ ou -)")
        if not _VERSION_RE.fullmatch(self.version):
            raise ValueError("version attendue: AAAA.N ou AAAA.N.N")
        return self


class ApprovalRequest(BaseModel):
    note: str = Field(min_length=3, max_length=1000)


class EvidenceRequest(BaseModel):
    code: str
    reference: str = Field(min_length=3, max_length=255)
    issued_at: datetime
    note: str | None = Field(default=None, max_length=1500)


class DossierCreate(BaseModel):
    title: str = Field(min_length=5, max_length=255)
    policy_reference: str = Field(min_length=5, max_length=120)
    target_scope: str = Field(default="national", pattern=r"^(pilot|national)$")


def policy_reference(code: str, version: str) -> str:
    return f"DNTT-POLICY-{code}-{version}"


def technical_contract() -> dict:
    return {
        "question_count": EXAM_QUESTIONS_TOTAL,
        "pass_threshold": EXAM_PASS_THRESHOLD,
        "duration_minutes": EXAM_DURATION_MINUTES,
        "category_distribution": dict(CATEGORY_DISTRIBUTION),
        "one_attempt_per_session": True,
    }


def compare_policy_to_runtime(parameters: dict) -> dict:
    runtime = technical_contract()
    drift: list[dict] = []
    for field in ("question_count", "pass_threshold", "duration_minutes", "one_attempt_per_session"):
        if parameters.get(field) != runtime[field]:
            drift.append({"field": field, "policy": parameters.get(field), "runtime": runtime[field]})
    if parameters.get("category_distribution") != runtime["category_distribution"]:
        drift.append(
            {
                "field": "category_distribution",
                "policy": parameters.get("category_distribution"),
                "runtime": runtime["category_distribution"],
            }
        )
    return {"aligned": not drift, "runtime": runtime, "drift": drift}


def _policy_record(db: Session, reference: str) -> tuple[InstitutionalAuthorization, dict]:
    record = db.scalar(select(InstitutionalAuthorization).where(InstitutionalAuthorization.reference == reference))
    if not record:
        raise HTTPException(status_code=404, detail="Politique institutionnelle introuvable")
    document = _load(record)
    if document.get("kind") != POLICY_KIND:
        raise HTTPException(status_code=409, detail="La référence ne désigne pas une politique nationale")
    return record, document


def _dossier_record(db: Session, reference: str) -> tuple[InstitutionalAuthorization, dict]:
    record = db.scalar(select(InstitutionalAuthorization).where(InstitutionalAuthorization.reference == reference))
    if not record:
        raise HTTPException(status_code=404, detail="Dossier d'homologation introuvable")
    document = _load(record)
    if document.get("kind") != DOSSIER_KIND:
        raise HTTPException(status_code=409, detail="La référence ne désigne pas un dossier d'homologation")
    return record, document


def _audit(db: Session, actor: User, action: str, entity_id: str, details: dict) -> None:
    db.add(
        AuditLog(
            actor_id=actor.id,
            action=action,
            entity="national_governance",
            entity_id=entity_id if len(entity_id) <= 36 else None,
            details={"reference": entity_id, **details},
        )
    )


def _serialize(record: InstitutionalAuthorization, document: dict) -> dict:
    return {
        "id": record.id,
        "reference": record.reference,
        "authority": record.authority,
        "title": record.title,
        "status": record.status,
        "valid_from": record.valid_from.isoformat() if record.valid_from else None,
        "valid_until": record.valid_until.isoformat() if record.valid_until else None,
        "created_at": record.created_at.isoformat() if record.created_at else None,
        "updated_at": record.updated_at.isoformat() if record.updated_at else None,
        "document": document,
    }


def create_policy(db: Session, actor: User, payload: PolicyCreate) -> dict:
    reference = policy_reference(payload.code, payload.version)
    if db.scalar(select(InstitutionalAuthorization.id).where(InstitutionalAuthorization.reference == reference)):
        raise HTTPException(status_code=409, detail="Cette version de politique existe déjà")
    document = {
        "kind": POLICY_KIND,
        "schema_version": 1,
        "code": payload.code,
        "version": payload.version,
        "parameters": payload.parameters.model_dump(),
        "legal_references": [item.model_dump() for item in payload.legal_references],
        "rationale": payload.rationale,
        "created_by": actor.id,
        "created_at": _now().isoformat(),
        "submitted_by": None,
        "submitted_at": None,
        "approvals": [],
        "activated_by": None,
        "activated_at": None,
        "supersedes_reference": None,
    }
    record = InstitutionalAuthorization(
        authority=payload.authority,
        reference=reference,
        title=payload.title,
        scope=_dump(document),
        status="draft",
    )
    db.add(record)
    db.flush()
    _audit(db, actor, "governance.policy_created", reference, {"code": payload.code, "version": payload.version})
    db.commit()
    db.refresh(record)
    return _serialize(record, _load(record))


def submit_policy(db: Session, actor: User, reference: str) -> dict:
    record, document = _policy_record(db, reference)
    if record.status != "draft":
        raise HTTPException(status_code=409, detail="Seule une politique draft peut être soumise")
    document["submitted_by"] = actor.id
    document["submitted_at"] = _now().isoformat()
    record.status = "pending_approval"
    record.updated_at = _naive()
    record.scope = _dump(document)
    _audit(db, actor, "governance.policy_submitted", reference, {})
    db.commit()
    return _serialize(record, _load(record))


def approve_policy(db: Session, actor: User, reference: str, note: str) -> dict:
    record, document = _policy_record(db, reference)
    if record.status not in {"pending_approval", "approved"}:
        raise HTTPException(status_code=409, detail="Politique non soumise à approbation")
    if document.get("created_by") == actor.id:
        raise HTTPException(status_code=409, detail="Le rédacteur ne peut pas approuver sa propre politique")
    approvals = list(document.get("approvals") or [])
    if any(item.get("actor_id") == actor.id for item in approvals):
        raise HTTPException(status_code=409, detail="Cet acteur a déjà approuvé cette politique")
    approvals.append({"actor_id": actor.id, "role": actor.role, "approved_at": _now().isoformat(), "note": note})
    document["approvals"] = approvals
    if len({item["actor_id"] for item in approvals}) >= 2:
        record.status = "approved"
    record.updated_at = _naive()
    record.scope = _dump(document)
    _audit(db, actor, "governance.policy_approved", reference, {"approval_count": len(approvals)})
    db.commit()
    return _serialize(record, _load(record))


def activate_policy(db: Session, actor: User, reference: str) -> dict:
    record, document = _policy_record(db, reference)
    if actor.role != "super_admin":
        raise HTTPException(status_code=403, detail="Activation réservée au super_admin")
    if record.status != "approved":
        raise HTTPException(status_code=409, detail="Deux approbations distinctes sont requises avant activation")
    approvals = {item.get("actor_id") for item in document.get("approvals") or []}
    if len(approvals) < 2:
        raise HTTPException(status_code=409, detail="Séparation des tâches insuffisante")
    alignment = compare_policy_to_runtime(document["parameters"])
    if not alignment["aligned"]:
        raise HTTPException(
            status_code=409,
            detail={"code": "TECHNICAL_CONFIGURATION_MISMATCH", **alignment},
        )

    previous = db.scalars(
        select(InstitutionalAuthorization).where(
            InstitutionalAuthorization.status == "active",
            InstitutionalAuthorization.reference.like("DNTT-POLICY-%"),
        )
    ).all()
    for item in previous:
        previous_doc = _load(item)
        if previous_doc.get("kind") != POLICY_KIND or previous_doc.get("code") != document.get("code"):
            continue
        item.status = "superseded"
        item.valid_until = _naive()
        item.updated_at = _naive()
        document["supersedes_reference"] = item.reference

    record.status = "active"
    record.valid_from = _naive()
    record.updated_at = _naive()
    document["activated_by"] = actor.id
    document["activated_at"] = _now().isoformat()
    record.scope = _dump(document)
    _audit(db, actor, "governance.policy_activated", reference, {"supersedes": document.get("supersedes_reference")})
    db.commit()
    return _serialize(record, _load(record))


def revoke_policy(db: Session, actor: User, reference: str, reason: str) -> dict:
    record, document = _policy_record(db, reference)
    if actor.role != "super_admin":
        raise HTTPException(status_code=403, detail="Révocation réservée au super_admin")
    if record.status not in {"approved", "active"}:
        raise HTTPException(status_code=409, detail="Cette politique ne peut pas être révoquée dans son état actuel")
    record.status = "revoked"
    record.valid_until = _naive()
    record.updated_at = _naive()
    document["revoked_by"] = actor.id
    document["revoked_at"] = _now().isoformat()
    document["revocation_reason"] = reason[:1500]
    record.scope = _dump(document)
    _audit(db, actor, "governance.policy_revoked", reference, {"reason": reason[:500]})
    db.commit()
    return _serialize(record, _load(record))


def list_policies(db: Session) -> list[dict]:
    records = db.scalars(
        select(InstitutionalAuthorization)
        .where(InstitutionalAuthorization.reference.like("DNTT-POLICY-%"))
        .order_by(InstitutionalAuthorization.created_at.desc())
    ).all()
    result = []
    for record in records:
        try:
            document = _load(record)
        except HTTPException:
            continue
        if document.get("kind") == POLICY_KIND:
            result.append(_serialize(record, document))
    return result


def active_policy(db: Session) -> dict | None:
    records = db.scalars(
        select(InstitutionalAuthorization).where(
            InstitutionalAuthorization.status == "active",
            InstitutionalAuthorization.reference.like("DNTT-POLICY-%"),
        )
    ).all()
    policies = []
    for record in records:
        document = _load(record)
        if document.get("kind") == POLICY_KIND:
            policies.append((record, document))
    if len(policies) > 1:
        raise HTTPException(status_code=409, detail={"code": "MULTIPLE_ACTIVE_NATIONAL_POLICIES", "count": len(policies)})
    return _serialize(*policies[0]) if policies else None


def _latest_evidence_time(db: Session, action: str) -> datetime | None:
    row = db.scalar(select(AuditLog).where(AuditLog.action == action).order_by(AuditLog.created_at.desc()).limit(1))
    if not row:
        return None
    details = row.details if isinstance(row.details, dict) else {}
    raw = details.get("occurred_at")
    if isinstance(raw, str):
        try:
            parsed = datetime.fromisoformat(raw)
            return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)
        except ValueError:
            pass
    created = row.created_at
    return created.replace(tzinfo=UTC) if created and created.tzinfo is None else created


def build_readiness(db: Session) -> dict:
    policy = active_policy(db)
    checks: list[dict] = []

    if policy:
        alignment = compare_policy_to_runtime(policy["document"]["parameters"])
        checks.append({"code": "active_policy", "required": True, "status": "pass", "evidence": policy["reference"]})
        checks.append(
            {
                "code": "runtime_alignment",
                "required": True,
                "status": "pass" if alignment["aligned"] else "fail",
                "evidence": alignment,
            }
        )
        parameters = policy["document"]["parameters"]
        approved = list(
            db.scalars(
                select(Question).where(Question.is_active.is_(True), Question.validation_status == "approved")
            ).all()
        )
        official = filter_official_exam_pool(approved)
        category_counts: dict[str, int] = {}
        for question in official:
            category_counts[question.category] = category_counts.get(question.category, 0) + 1
        missing = {
            category: max(0, int(required) - category_counts.get(category, 0))
            for category, required in parameters["category_distribution"].items()
            if category_counts.get(category, 0) < int(required)
        }
        checks.append(
            {
                "code": "official_question_bank",
                "required": True,
                "status": "pass" if len(official) >= parameters["question_count"] and not missing else "fail",
                "evidence": {"eligible": len(official), "required": parameters["question_count"], "category_shortfall": missing},
            }
        )
    else:
        checks.extend(
            [
                {"code": "active_policy", "required": True, "status": "fail", "evidence": None},
                {"code": "runtime_alignment", "required": True, "status": "fail", "evidence": {"reason": "no_active_policy"}},
                {"code": "official_question_bank", "required": True, "status": "fail", "evidence": {"reason": "no_active_policy"}},
            ]
        )

    accredited = int(
        db.scalar(select(func.count(Center.id)).where(Center.status.in_(["active", "accredited"]))) or 0
    )
    checks.append(
        {"code": "accredited_centers", "required": True, "status": "pass" if accredited > 0 else "fail", "evidence": {"count": accredited}}
    )

    now = _now()
    operational_evidence = [
        ("backup_off_region", "reliability.backup_uploaded", timedelta(hours=26)),
        ("restore_drill", "reliability.restore_drill_passed", timedelta(days=35)),
        ("api_failover", "reliability.ha_failover_probe_passed", timedelta(days=35)),
    ]
    for code, action, max_age in operational_evidence:
        occurred = _latest_evidence_time(db, action)
        fresh = bool(occurred and now - occurred.astimezone(UTC) <= max_age)
        checks.append(
            {
                "code": code,
                "required": True,
                "status": "pass" if fresh else "fail",
                "evidence": {"last_success": occurred.isoformat() if occurred else None, "max_age_seconds": int(max_age.total_seconds())},
            }
        )

    blockers = [item["code"] for item in checks if item["required"] and item["status"] != "pass"]
    return {
        "generated_at": now.isoformat(),
        "go_live_allowed": not blockers,
        "active_policy": policy,
        "checks": checks,
        "blockers": blockers,
    }


def create_dossier(db: Session, actor: User, payload: DossierCreate) -> dict:
    policy_record, policy_doc = _policy_record(db, payload.policy_reference)
    if policy_record.status != "active":
        raise HTTPException(status_code=409, detail="Le dossier doit référencer une politique active")
    reference = f"DNTT-HOMO-{_now().strftime('%Y%m%d%H%M%S')}-{actor.id[:6].upper()}"
    document = {
        "kind": DOSSIER_KIND,
        "schema_version": 1,
        "policy_reference": payload.policy_reference,
        "policy_sha256": policy_doc["document_sha256"],
        "target_scope": payload.target_scope,
        "created_by": actor.id,
        "created_at": _now().isoformat(),
        "evidence": {},
        "submitted_at": None,
        "approvals": [],
        "decision": None,
    }
    record = InstitutionalAuthorization(
        authority="DNTT",
        reference=reference,
        title=payload.title,
        scope=_dump(document),
        status="draft",
    )
    db.add(record)
    db.flush()
    _audit(db, actor, "governance.homologation_created", reference, {"policy_reference": payload.policy_reference})
    db.commit()
    return _serialize(record, _load(record))


def attach_evidence(db: Session, actor: User, reference: str, payload: EvidenceRequest) -> dict:
    record, document = _dossier_record(db, reference)
    if record.status not in {"draft", "evidence_review"}:
        raise HTTPException(status_code=409, detail="Le dossier n'accepte plus de nouvelles preuves")
    code = payload.code.strip().lower()
    if code not in MANDATORY_EVIDENCE:
        raise HTTPException(status_code=422, detail={"code": "UNKNOWN_HOMOLOGATION_EVIDENCE", "allowed": sorted(MANDATORY_EVIDENCE)})
    evidence = dict(document.get("evidence") or {})
    evidence[code] = {
        "reference": payload.reference,
        "issued_at": payload.issued_at.astimezone(UTC).isoformat(),
        "note": payload.note,
        "attached_by": actor.id,
        "attached_at": _now().isoformat(),
    }
    document["evidence"] = evidence
    record.status = "evidence_review"
    record.updated_at = _naive()
    record.scope = _dump(document)
    _audit(db, actor, "governance.homologation_evidence_attached", reference, {"evidence_code": code})
    db.commit()
    return _serialize(record, _load(record))


def submit_dossier(db: Session, actor: User, reference: str) -> dict:
    record, document = _dossier_record(db, reference)
    if record.status not in {"draft", "evidence_review"}:
        raise HTTPException(status_code=409, detail="Dossier non soumettable")
    missing = sorted(MANDATORY_EVIDENCE - set((document.get("evidence") or {}).keys()))
    if missing:
        raise HTTPException(status_code=409, detail={"code": "HOMOLOGATION_EVIDENCE_MISSING", "missing": missing})
    readiness = build_readiness(db)
    if not readiness["go_live_allowed"]:
        raise HTTPException(status_code=409, detail={"code": "NATIONAL_READINESS_BLOCKED", "blockers": readiness["blockers"]})
    document["submitted_by"] = actor.id
    document["submitted_at"] = _now().isoformat()
    document["readiness_snapshot"] = readiness
    record.status = "pending_approval"
    record.updated_at = _naive()
    record.scope = _dump(document)
    _audit(db, actor, "governance.homologation_submitted", reference, {"policy_reference": document["policy_reference"]})
    db.commit()
    return _serialize(record, _load(record))


def approve_dossier(db: Session, actor: User, reference: str, note: str) -> dict:
    record, document = _dossier_record(db, reference)
    if record.status not in {"pending_approval", "ready_for_decision"}:
        raise HTTPException(status_code=409, detail="Dossier non soumis à approbation")
    if document.get("created_by") == actor.id:
        raise HTTPException(status_code=409, detail="Le créateur du dossier ne peut pas l'approuver")
    approvals = list(document.get("approvals") or [])
    if any(item.get("actor_id") == actor.id for item in approvals):
        raise HTTPException(status_code=409, detail="Cet acteur a déjà approuvé le dossier")
    approvals.append({"actor_id": actor.id, "role": actor.role, "approved_at": _now().isoformat(), "note": note})
    document["approvals"] = approvals
    if len({item["actor_id"] for item in approvals}) >= 2:
        record.status = "ready_for_decision"
    record.updated_at = _naive()
    record.scope = _dump(document)
    _audit(db, actor, "governance.homologation_approved", reference, {"approval_count": len(approvals)})
    db.commit()
    return _serialize(record, _load(record))


def decide_dossier(db: Session, actor: User, reference: str, *, approve: bool, note: str) -> dict:
    record, document = _dossier_record(db, reference)
    if actor.role != "super_admin":
        raise HTTPException(status_code=403, detail="Décision finale réservée au super_admin")
    if record.status != "ready_for_decision":
        raise HTTPException(status_code=409, detail="Deux approbations sont requises avant décision")
    current_policy = active_policy(db)
    if not current_policy or current_policy["reference"] != document["policy_reference"]:
        raise HTTPException(status_code=409, detail="La politique active a changé depuis la création du dossier")
    if current_policy["document"]["document_sha256"] != document["policy_sha256"]:
        raise HTTPException(status_code=409, detail="La politique active ne correspond plus à l'empreinte du dossier")
    readiness = build_readiness(db)
    if approve and not readiness["go_live_allowed"]:
        raise HTTPException(status_code=409, detail={"code": "NATIONAL_READINESS_BLOCKED", "blockers": readiness["blockers"]})
    document["decision"] = {
        "status": "homologated" if approve else "rejected",
        "decided_by": actor.id,
        "decided_at": _now().isoformat(),
        "note": note,
        "readiness_snapshot": readiness,
    }
    record.status = "homologated" if approve else "rejected"
    record.valid_from = _naive() if approve else None
    record.updated_at = _naive()
    record.scope = _dump(document)
    _audit(db, actor, "governance.homologation_decided", reference, {"decision": record.status, "policy_reference": document["policy_reference"]})
    db.commit()
    return _serialize(record, _load(record))


def list_dossiers(db: Session) -> list[dict]:
    records = db.scalars(
        select(InstitutionalAuthorization)
        .where(InstitutionalAuthorization.reference.like("DNTT-HOMO-%"))
        .order_by(InstitutionalAuthorization.created_at.desc())
    ).all()
    result = []
    for record in records:
        try:
            document = _load(record)
        except HTTPException:
            continue
        if document.get("kind") == DOSSIER_KIND:
            result.append(_serialize(record, document))
    return result
