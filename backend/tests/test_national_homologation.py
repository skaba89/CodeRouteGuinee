import pytest
from fastapi import HTTPException
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
    activate_policy,
    approve_policy,
    create_dossier,
    create_policy,
    submit_dossier,
    submit_policy,
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
        code="P12_HOMO_B",
        version="2098.1",
        title="Politique de recette homologation P12",
        authority="DNTT",
        parameters=ExamPolicyParameters(
            question_count=EXAM_QUESTIONS_TOTAL,
            pass_threshold=EXAM_PASS_THRESHOLD,
            duration_minutes=EXAM_DURATION_MINUTES,
            category_distribution=dict(CATEGORY_DISTRIBUTION),
            one_attempt_per_session=True,
            retake_cooldown_hours=0,
        ),
        legal_references=[LegalReference(reference="DNTT-HOMO-TEST", title="Décision de recette P12")],
        rationale="Politique alignée sur le runtime afin de tester le dossier d'homologation.",
    )
    reference = create_policy(db, creator, payload)["reference"]
    submit_policy(db, creator, reference)
    approve_policy(db, approver1, reference, "Validation 1")
    approve_policy(db, approver2, reference, "Validation 2")
    activate_policy(db, approver2, reference)
    return reference


def test_homologation_dossier_requires_all_institutional_evidence_before_submit() -> None:
    init_db()
    creator = _user("00000000-0000-4000-8000-000000000141", "admin")
    approver1 = _user("00000000-0000-4000-8000-000000000142", "admin")
    approver2 = _user("00000000-0000-4000-8000-000000000143", "super_admin")

    with SessionLocal() as db:
        _reset(db)
        policy_reference = _active_policy(db, creator, approver1, approver2)
        dossier = create_dossier(
            db,
            creator,
            DossierCreate(
                title="Recette homologation nationale",
                policy_reference=policy_reference,
                target_scope="national",
            ),
        )
        assert dossier["status"] == "draft"
        assert dossier["document"]["policy_reference"] == policy_reference
        assert dossier["document"]["policy_sha256"]

        with pytest.raises(HTTPException) as blocked:
            submit_dossier(db, creator, dossier["reference"])
        assert blocked.value.status_code == 409
        assert blocked.value.detail["code"] == "HOMOLOGATION_EVIDENCE_MISSING"
        assert set(blocked.value.detail["missing"]) == MANDATORY_EVIDENCE
