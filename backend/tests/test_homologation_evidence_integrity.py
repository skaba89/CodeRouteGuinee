from datetime import UTC, datetime, timedelta

import pytest
from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import delete

from app.db.session import SessionLocal, init_db
from app.exam_engine import CATEGORY_DISTRIBUTION, EXAM_DURATION_MINUTES, EXAM_PASS_THRESHOLD, EXAM_QUESTIONS_TOTAL
from app.models_institutional_authorization import InstitutionalAuthorization
from app.models_user import User
from app.national_governance import (
    DossierCreate,
    ExamPolicyParameters,
    LegalReference,
    MANDATORY_EVIDENCE,
    PolicyCreate,
    _dossier_record,
    _dump,
    activate_policy,
    approve_policy,
    create_dossier,
    create_policy,
    submit_policy,
)
from app.national_governance_evidence import (
    EvidenceIntegrityRequest,
    attach_hashed_evidence,
    validate_dossier_evidence_integrity,
)


def _user(identifier: str, role: str) -> User:
    return User(
        id=identifier,
        email=f"{identifier}@example.test",
        full_name=identifier,
        password_hash="not-used",
        role=role,
        is_active=True,
    )


def _reset(db) -> None:
    db.execute(
        delete(InstitutionalAuthorization).where(
            InstitutionalAuthorization.reference.like("DNTT-POLICY-%")
            | InstitutionalAuthorization.reference.like("DNTT-HOMO-%")
        )
    )
    db.commit()


def _active_policy(db, creator: User, approver1: User, approver2: User) -> str:
    payload = PolicyCreate(
        code="P12_HASHED_EVIDENCE",
        version="2097.1",
        title="Politique P12 preuves hashées",
        authority="DNTT",
        parameters=ExamPolicyParameters(
            question_count=EXAM_QUESTIONS_TOTAL,
            pass_threshold=EXAM_PASS_THRESHOLD,
            duration_minutes=EXAM_DURATION_MINUTES,
            category_distribution=dict(CATEGORY_DISTRIBUTION),
            one_attempt_per_session=True,
            retake_cooldown_hours=0,
        ),
        legal_references=[LegalReference(reference="DNTT-HASH-TEST", title="Décision de recette preuves hashées")],
        rationale="Politique alignée au runtime pour valider l'intégrité des pièces d'homologation.",
    )
    reference = create_policy(db, creator, payload)["reference"]
    submit_policy(db, creator, reference)
    approve_policy(db, approver1, reference, "Validation intégrité 1")
    approve_policy(db, approver2, reference, "Validation intégrité 2")
    activate_policy(db, approver2, reference)
    return reference


def _dossier(db, creator: User, approver1: User, approver2: User) -> str:
    policy_reference = _active_policy(db, creator, approver1, approver2)
    return create_dossier(
        db,
        creator,
        DossierCreate(
            title="Dossier P12 avec preuves SHA-256",
            policy_reference=policy_reference,
            target_scope="national",
        ),
    )["reference"]


def _payload(code: str, digest_char: str = "a", *, issued_at: datetime | None = None) -> EvidenceIntegrityRequest:
    return EvidenceIntegrityRequest(
        code=code,
        reference=f"GED-DNTT-{code.upper()}-2026-001",
        artifact_sha256=digest_char * 64,
        issued_at=issued_at or datetime.now(UTC),
        note="Pièce institutionnelle archivée dans la GED de recette.",
    )


def test_evidence_request_rejects_invalid_hash_and_external_url_reference() -> None:
    with pytest.raises(ValidationError, match="artifact_sha256"):
        EvidenceIntegrityRequest(
            code="legal_review",
            reference="GED-DNTT-LEGAL-001",
            artifact_sha256="abcd",
            issued_at=datetime.now(UTC),
        )

    with pytest.raises(ValidationError, match="identifiant GED interne"):
        EvidenceIntegrityRequest(
            code="legal_review",
            reference="https://ged.example/document/1?token=secret",
            artifact_sha256="a" * 64,
            issued_at=datetime.now(UTC),
        )


def test_hashed_evidence_is_stored_and_replacement_history_is_append_only() -> None:
    init_db()
    creator = _user("00000000-0000-4000-8000-000000000241", "admin")
    approver1 = _user("00000000-0000-4000-8000-000000000242", "admin")
    approver2 = _user("00000000-0000-4000-8000-000000000243", "super_admin")

    with SessionLocal() as db:
        _reset(db)
        reference = _dossier(db, creator, approver1, approver2)
        first = attach_hashed_evidence(db, creator, reference, _payload("legal_review", "a"))
        assert first["document"]["evidence"]["legal_review"]["artifact_sha256"] == "a" * 64
        assert first["document"].get("evidence_history") == []

        replacement = attach_hashed_evidence(db, creator, reference, _payload("legal_review", "b"))
        assert replacement["document"]["evidence"]["legal_review"]["artifact_sha256"] == "b" * 64
        history = replacement["document"]["evidence_history"]
        assert len(history) == 1
        assert history[0]["artifact_sha256"] == "a" * 64
        assert history[0]["code"] == "legal_review"


def test_integrity_validator_requires_all_five_hashes() -> None:
    init_db()
    creator = _user("00000000-0000-4000-8000-000000000251", "admin")
    approver1 = _user("00000000-0000-4000-8000-000000000252", "admin")
    approver2 = _user("00000000-0000-4000-8000-000000000253", "super_admin")

    with SessionLocal() as db:
        _reset(db)
        reference = _dossier(db, creator, approver1, approver2)
        for index, code in enumerate(sorted(MANDATORY_EVIDENCE)):
            attach_hashed_evidence(db, creator, reference, _payload(code, chr(ord("a") + index)))

        result = validate_dossier_evidence_integrity(db, reference)
        assert result["valid"] is True
        assert result["evidence_count"] == 5
        assert set(result["hashes"]) == MANDATORY_EVIDENCE

        record, document = _dossier_record(db, reference)
        document["evidence"]["security_assessment"].pop("artifact_sha256", None)
        record.scope = _dump(document)
        db.commit()

        with pytest.raises(HTTPException) as invalid:
            validate_dossier_evidence_integrity(db, reference)
        assert invalid.value.status_code == 409
        assert invalid.value.detail["code"] == "HOMOLOGATION_EVIDENCE_INTEGRITY_INVALID"
        assert {item["code"] for item in invalid.value.detail["invalid"]} == {"security_assessment"}


def test_evidence_issued_in_the_future_is_rejected() -> None:
    init_db()
    creator = _user("00000000-0000-4000-8000-000000000261", "admin")
    approver1 = _user("00000000-0000-4000-8000-000000000262", "admin")
    approver2 = _user("00000000-0000-4000-8000-000000000263", "super_admin")

    with SessionLocal() as db:
        _reset(db)
        reference = _dossier(db, creator, approver1, approver2)
        with pytest.raises(HTTPException) as future:
            attach_hashed_evidence(
                db,
                creator,
                reference,
                _payload("content_signoff", "f", issued_at=datetime.now(UTC) + timedelta(hours=1)),
            )
        assert future.value.status_code == 422
        assert "tolérance" in str(future.value.detail)
