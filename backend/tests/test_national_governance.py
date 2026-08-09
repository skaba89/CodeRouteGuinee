import json

import pytest
from fastapi import HTTPException
from sqlalchemy import delete, select

from app.db.session import SessionLocal, init_db
from app.exam_engine import CATEGORY_DISTRIBUTION, EXAM_DURATION_MINUTES, EXAM_PASS_THRESHOLD, EXAM_QUESTIONS_TOTAL
from app.models_institutional_authorization import InstitutionalAuthorization
from app.models_user import User
from app.national_governance import (
    ExamPolicyParameters,
    LegalReference,
    PolicyCreate,
    activate_policy,
    approve_policy,
    compare_policy_to_runtime,
    create_policy,
    submit_policy,
)
from app.national_governance_guard import assert_single_active_policy_code


def _user(identifier: str, role: str) -> User:
    return User(
        id=identifier,
        email=f"{identifier}@example.test",
        full_name=identifier,
        password_hash="not-used",
        role=role,
        is_active=True,
    )


def _reset_governance(db) -> None:
    db.execute(
        delete(InstitutionalAuthorization).where(
            InstitutionalAuthorization.reference.like("DNTT-POLICY-%")
            | InstitutionalAuthorization.reference.like("DNTT-HOMO-%")
        )
    )
    db.commit()


def _payload(code: str, version: str = "2099.1", *, question_count: int | None = None) -> PolicyCreate:
    count = question_count or EXAM_QUESTIONS_TOTAL
    distribution = dict(CATEGORY_DISTRIBUTION)
    if count != EXAM_QUESTIONS_TOTAL:
        first = next(iter(distribution))
        distribution[first] += count - EXAM_QUESTIONS_TOTAL
    return PolicyCreate(
        code=code,
        version=version,
        title=f"Politique officielle {code}",
        authority="DNTT",
        parameters=ExamPolicyParameters(
            question_count=count,
            pass_threshold=min(EXAM_PASS_THRESHOLD, count),
            duration_minutes=EXAM_DURATION_MINUTES,
            category_distribution=distribution,
            one_attempt_per_session=True,
            retake_cooldown_hours=0,
        ),
        legal_references=[
            LegalReference(
                reference="DNTT-RECETTE-2099",
                title="Référence de recette institutionnelle",
                source_ref="Dossier de validation DNTT",
            )
        ],
        rationale="Recette P12 de la gouvernance nationale versionnée.",
    )


def _approve(db, creator: User, approver1: User, approver2: User, code: str, version: str = "2099.1") -> str:
    created = create_policy(db, creator, _payload(code, version=version))
    reference = created["reference"]
    submit_policy(db, creator, reference)
    approve_policy(db, approver1, reference, "Première validation indépendante")
    approve_policy(db, approver2, reference, "Deuxième validation indépendante")
    return reference


def test_runtime_contract_is_explicit_and_aligned() -> None:
    payload = _payload("P12ALIGN")
    result = compare_policy_to_runtime(payload.parameters.model_dump())
    assert result["aligned"] is True
    assert result["drift"] == []


def test_policy_requires_four_eyes_before_activation() -> None:
    init_db()
    creator = _user("00000000-0000-4000-8000-000000000121", "admin")
    approver1 = _user("00000000-0000-4000-8000-000000000122", "admin")
    approver2 = _user("00000000-0000-4000-8000-000000000123", "super_admin")

    with SessionLocal() as db:
        _reset_governance(db)
        created = create_policy(db, creator, _payload("P12FOUREYES"))
        reference = created["reference"]
        submitted = submit_policy(db, creator, reference)
        assert submitted["status"] == "pending_approval"

        with pytest.raises(HTTPException) as own_approval:
            approve_policy(db, creator, reference, "Auto-approbation interdite")
        assert own_approval.value.status_code == 409

        first = approve_policy(db, approver1, reference, "Validation métier indépendante")
        assert first["status"] == "pending_approval"
        second = approve_policy(db, approver2, reference, "Validation institutionnelle indépendante")
        assert second["status"] == "approved"
        assert len(second["document"]["approvals"]) == 2

        active = activate_policy(db, approver2, reference)
        assert active["status"] == "active"
        assert active["document"]["activated_by"] == approver2.id


def test_approved_policy_with_runtime_drift_cannot_activate() -> None:
    init_db()
    creator = _user("00000000-0000-4000-8000-000000000124", "admin")
    approver1 = _user("00000000-0000-4000-8000-000000000125", "admin")
    approver2 = _user("00000000-0000-4000-8000-000000000126", "super_admin")

    with SessionLocal() as db:
        _reset_governance(db)
        created = create_policy(db, creator, _payload("P12DRIFT", version="2099.2", question_count=EXAM_QUESTIONS_TOTAL + 1))
        reference = created["reference"]
        submit_policy(db, creator, reference)
        approve_policy(db, approver1, reference, "Première validation")
        approve_policy(db, approver2, reference, "Deuxième validation")

        with pytest.raises(HTTPException) as blocked:
            activate_policy(db, approver2, reference)
        assert blocked.value.status_code == 409
        assert blocked.value.detail["code"] == "TECHNICAL_CONFIGURATION_MISMATCH"
        assert any(item["field"] == "question_count" for item in blocked.value.detail["drift"])


def test_policy_document_tamper_is_detected() -> None:
    init_db()
    creator = _user("00000000-0000-4000-8000-000000000127", "admin")
    with SessionLocal() as db:
        _reset_governance(db)
        created = create_policy(db, creator, _payload("P12TAMPER", version="2099.3"))
        reference = created["reference"]
        record = db.scalar(select(InstitutionalAuthorization).where(InstitutionalAuthorization.reference == reference))
        assert record is not None
        document = json.loads(record.scope)
        document["rationale"] = "altération directe hors workflow"
        record.scope = json.dumps(document)
        db.commit()

        with pytest.raises(HTTPException) as tampered:
            submit_policy(db, creator, reference)
        assert tampered.value.status_code == 409
        assert tampered.value.detail["code"] == "INSTITUTIONAL_DOCUMENT_HASH_MISMATCH"


def test_second_active_policy_code_is_blocked_while_runtime_is_single_policy() -> None:
    init_db()
    creator = _user("00000000-0000-4000-8000-000000000128", "admin")
    approver1 = _user("00000000-0000-4000-8000-000000000129", "admin")
    approver2 = _user("00000000-0000-4000-8000-000000000130", "super_admin")

    with SessionLocal() as db:
        _reset_governance(db)
        first_reference = _approve(db, creator, approver1, approver2, "CATEGORY_B", version="2099.4")
        activate_policy(db, approver2, first_reference)

        second_reference = _approve(db, creator, approver1, approver2, "CATEGORY_C", version="2099.5")
        with pytest.raises(HTTPException) as conflict:
            assert_single_active_policy_code(db, second_reference)
        assert conflict.value.status_code == 409
        assert conflict.value.detail["code"] == "ACTIVE_POLICY_CODE_CONFLICT"
        assert conflict.value.detail["active_reference"] == first_reference
