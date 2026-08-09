from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.deps import require_roles
from app.models_user import User
from app.national_governance import (
    ApprovalRequest,
    DossierCreate,
    EvidenceRequest,
    PolicyCreate,
    active_policy,
    activate_policy,
    approve_dossier,
    approve_policy,
    attach_evidence,
    build_readiness,
    compare_policy_to_runtime,
    create_dossier,
    create_policy,
    decide_dossier,
    list_dossiers,
    list_policies,
    revoke_policy,
    submit_dossier,
    submit_policy,
    technical_contract,
)
from app.national_governance_guard import assert_single_active_policy_code

router = APIRouter(prefix="/national-governance", tags=["national-governance"])


@router.get("/technical-contract")
def get_technical_contract(
    db: Session = Depends(get_db),
    _user: User = Depends(require_roles("admin", "super_admin")),
) -> dict:
    policy = active_policy(db)
    return {
        "runtime": technical_contract(),
        "active_policy": policy,
        "alignment": (
            compare_policy_to_runtime(policy["document"]["parameters"])
            if policy
            else {"aligned": False, "drift": [{"field": "active_policy", "policy": None, "runtime": "required"}]}
        ),
    }


@router.get("/readiness")
def national_governance_readiness(
    db: Session = Depends(get_db),
    _user: User = Depends(require_roles("admin", "super_admin")),
) -> dict:
    return build_readiness(db)


@router.get("/policies")
def policies(
    db: Session = Depends(get_db),
    _user: User = Depends(require_roles("admin", "super_admin")),
) -> list[dict]:
    return list_policies(db)


@router.get("/policies/active")
def policy_active(
    db: Session = Depends(get_db),
    _user: User = Depends(require_roles("admin", "super_admin")),
) -> dict:
    return {"policy": active_policy(db)}


@router.post("/policies", status_code=201)
def policy_create(
    payload: PolicyCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("admin", "super_admin")),
) -> dict:
    return create_policy(db, user, payload)


@router.post("/policies/{reference}/submit")
def policy_submit(
    reference: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("admin", "super_admin")),
) -> dict:
    return submit_policy(db, user, reference)


@router.post("/policies/{reference}/approve")
def policy_approve(
    reference: str,
    payload: ApprovalRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("admin", "super_admin")),
) -> dict:
    return approve_policy(db, user, reference, payload.note)


@router.post("/policies/{reference}/activate")
def policy_activate(
    reference: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("super_admin")),
) -> dict:
    assert_single_active_policy_code(db, reference)
    return activate_policy(db, user, reference)


@router.post("/policies/{reference}/revoke")
def policy_revoke(
    reference: str,
    reason: str = Query(min_length=5, max_length=1500),
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("super_admin")),
) -> dict:
    return revoke_policy(db, user, reference, reason)


@router.get("/homologation-dossiers")
def homologation_dossiers(
    db: Session = Depends(get_db),
    _user: User = Depends(require_roles("admin", "super_admin")),
) -> list[dict]:
    return list_dossiers(db)


@router.post("/homologation-dossiers", status_code=201)
def homologation_create(
    payload: DossierCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("admin", "super_admin")),
) -> dict:
    return create_dossier(db, user, payload)


@router.post("/homologation-dossiers/{reference}/evidence")
def homologation_evidence(
    reference: str,
    payload: EvidenceRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("admin", "super_admin")),
) -> dict:
    return attach_evidence(db, user, reference, payload)


@router.post("/homologation-dossiers/{reference}/submit")
def homologation_submit(
    reference: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("admin", "super_admin")),
) -> dict:
    return submit_dossier(db, user, reference)


@router.post("/homologation-dossiers/{reference}/approve")
def homologation_approve(
    reference: str,
    payload: ApprovalRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("admin", "super_admin")),
) -> dict:
    return approve_dossier(db, user, reference, payload.note)


@router.post("/homologation-dossiers/{reference}/decision")
def homologation_decision(
    reference: str,
    approve: bool,
    payload: ApprovalRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("super_admin")),
) -> dict:
    return decide_dossier(db, user, reference, approve=approve, note=payload.note)
