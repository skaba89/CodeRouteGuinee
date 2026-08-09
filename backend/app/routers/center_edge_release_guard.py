from __future__ import annotations

import math
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit_chain import append_audit
from app.db.session import get_db
from app.deps import require_roles
from app.edge_gateway import EDGE_AUTHORITY, decode_edge_scope, node_is_online
from app.edge_release import decode_attestation_scope, decode_release_scope, encode_release_scope, release_is_eligible
from app.models_institutional_authorization import InstitutionalAuthorization
from app.models_user import User
from app.routers.center_edge_release import (
    EDGE_RELEASE_ATTESTATION_AUTHORITY,
    EdgeReleaseAttestationRequest,
    EdgeReleaseRolloutUpdate,
    _release_by_id,
    attest_edge_release as _attest_edge_release,
    update_release_rollout as _update_release_rollout,
)

router = APIRouter(tags=["center-edge-release-guard"])


def _active_edge_nodes(db: Session) -> list[InstitutionalAuthorization]:
    return list(db.scalars(select(InstitutionalAuthorization).where(
        InstitutionalAuthorization.authority == EDGE_AUTHORITY,
        InstitutionalAuthorization.status == "active",
    )).all())


def _assert_canaries_trusted(db: Session, node_ids: list[str]) -> None:
    requested = set(node_ids)
    if not requested:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Au moins un gateway canary est requis")
    found: set[str] = set()
    unavailable: list[str] = []
    for node in _active_edge_nodes(db):
        if node.id not in requested:
            continue
        found.add(node.id)
        try:
            scope = decode_edge_scope(node.scope)
        except ValueError:
            unavailable.append(node.id)
            continue
        if not node_is_online(scope):
            unavailable.append(node.id)
    missing = sorted(requested - found)
    if missing or unavailable:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "EDGE_CANARY_NOT_READY",
                "message": "Tous les gateways canary doivent être actifs et en ligne au démarrage du canary.",
                "missing_node_ids": missing,
                "unavailable_node_ids": sorted(unavailable),
            },
        )


def _latest_attestations(db: Session, release_id: str) -> dict[str, str]:
    results: dict[str, str] = {}
    rows = list(db.scalars(select(InstitutionalAuthorization).where(
        InstitutionalAuthorization.authority == EDGE_RELEASE_ATTESTATION_AUTHORITY,
    )).all())
    for item in rows:
        try:
            scope = decode_attestation_scope(item.scope)
        except ValueError:
            continue
        if str(scope.get("release_id") or "") != release_id:
            continue
        node_id = str(scope.get("node_id") or "")
        result = str((scope.get("last_event") or {}).get("result") or item.status)
        if node_id:
            results[node_id] = result
    return results


def _eligible_node_ids(db: Session, scope: dict) -> set[str]:
    eligible: set[str] = set()
    for node in _active_edge_nodes(db):
        try:
            node_scope = decode_edge_scope(node.scope)
        except ValueError:
            continue
        center_id = str(node_scope.get("center_id") or "")
        if release_is_eligible(scope, node_id=node.id, center_id=center_id):
            eligible.add(node.id)
    return eligible


def _assert_previous_wave_healthy(db: Session, release: InstitutionalAuthorization, target: str, percent: int) -> None:
    scope = decode_release_scope(release.scope)
    previous = str(scope.get("rollout_status") or release.status)
    if target == "rolling" and previous not in {"canary", "rolling"}:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "EDGE_RELEASE_CANARY_REQUIRED", "message": "Un rollout progressif doit démarrer après un canary validé."},
        )
    if target == "released" and (previous != "rolling" or int(scope.get("rollout_percent") or 0) < 50):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "EDGE_RELEASE_ROLLING_REQUIRED", "message": "Le passage national exige une vague rolling d'au moins 50% validée."},
        )

    if target == "rolling" and previous == "rolling" and percent <= int(scope.get("rollout_percent") or 0):
        return

    eligible = _eligible_node_ids(db, scope)
    if not eligible:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "EDGE_RELEASE_NO_ELIGIBLE_NODES", "message": "La vague précédente ne contient aucun gateway éligible."},
        )
    attestations = _latest_attestations(db, release.id)
    failed = sorted(node_id for node_id, result in attestations.items() if node_id in eligible and result in {"failed", "rolled_back"})
    if failed:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "EDGE_RELEASE_HEALTH_GATE_FAILED",
                "message": "La promotion est bloquée : la vague précédente contient un échec ou rollback.",
                "failed_node_ids": failed,
            },
        )
    installed = sum(1 for node_id in eligible if attestations.get(node_id) == "installed")
    required_ratio = 1.0 if previous == "canary" else 0.8
    required = max(1, math.ceil(len(eligible) * required_ratio))
    if installed < required:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "EDGE_RELEASE_WAVE_NOT_VALIDATED",
                "message": "La vague précédente n'a pas assez d'installations attestées pour être élargie.",
                "eligible_nodes": len(eligible),
                "installed_nodes": installed,
                "required_installed_nodes": required,
            },
        )


def _assert_rollback_target_released(db: Session, release: InstitutionalAuthorization, payload: EdgeReleaseRolloutUpdate) -> None:
    scope = decode_release_scope(release.scope)
    rollback_id = payload.rollback_release_id or scope.get("rollback_release_id")
    if not rollback_id:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Une release de rollback est obligatoire")
    rollback = _release_by_id(db, str(rollback_id))
    if not rollback or rollback.id == release.id:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Release de rollback invalide")
    rollback_scope = decode_release_scope(rollback.scope)
    rollback_status = str(rollback_scope.get("rollout_status") or rollback.status)
    if rollback_status != "released":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "EDGE_ROLLBACK_TARGET_NOT_RELEASED",
                "message": "Le rollback doit cibler une version antérieure déjà validée et released.",
                "rollback_release_id": rollback.id,
                "rollback_status": rollback_status,
            },
        )


def _assert_attestation_matches_manifest(db: Session, payload: EdgeReleaseAttestationRequest) -> None:
    release = _release_by_id(db, payload.release_id)
    if not release:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Edge release not found")
    scope = decode_release_scope(release.scope)
    expected_version = str(scope["manifest"].get("software_version") or "")
    received_version = payload.software_version.strip()
    if received_version != expected_version:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "EDGE_RELEASE_VERSION_ATTESTATION_MISMATCH",
                "message": "La version attestée ne correspond pas au manifeste signé.",
                "expected_version": expected_version,
                "received_version": received_version,
            },
        )


@router.post("/releases/{release_id}/rollout")
def guarded_release_rollout(
    release_id: str,
    payload: EdgeReleaseRolloutUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("super_admin")),
) -> dict:
    release = _release_by_id(db, release_id, lock=True)
    if not release:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Edge release not found")
    target = payload.rollout_status.strip().lower()
    scope = decode_release_scope(release.scope)
    if target == "canary":
        canaries = payload.canary_node_ids if payload.canary_node_ids is not None else list(scope.get("canary_node_ids") or [])
        _assert_canaries_trusted(db, canaries)
    if target in {"rolling", "released"}:
        _assert_previous_wave_healthy(db, release, target, payload.rollout_percent)
    if target == "rollback":
        _assert_rollback_target_released(db, release, payload)
    return _update_release_rollout(release_id, payload, db, current_user)


@router.post("/release/attest")
def guarded_release_attestation(
    payload: EdgeReleaseAttestationRequest,
    db: Session = Depends(get_db),
) -> dict:
    _assert_attestation_matches_manifest(db, payload)
    response = _attest_edge_release(payload, db)
    if payload.result.strip().lower() != "failed":
        return response

    release = _release_by_id(db, payload.release_id, lock=True)
    if not release:
        return response
    scope = decode_release_scope(release.scope)
    previous = str(scope.get("rollout_status") or release.status)
    if previous in {"canary", "rolling", "released"}:
        now = datetime.now(UTC)
        scope["rollout_status"] = "paused"
        scope["last_rollout_reason"] = f"Pause automatique après échec attesté par le gateway {payload.node_id}"
        scope["last_rollout_by_id"] = None
        scope["last_rollout_at"] = now.isoformat().replace("+00:00", "Z")
        release.scope = encode_release_scope(scope)
        release.status = "paused"
        release.updated_at = now.replace(tzinfo=None)
        db.add(release)
        append_audit(
            db,
            actor_id=None,
            action="center_edge.release_auto_paused",
            entity="center_edge_release",
            entity_id=release.id,
            details={
                "previous_status": previous,
                "failed_node_id": payload.node_id,
                "center_id": payload.center_id,
                "software_version": payload.software_version,
                "artifact_sha256": payload.artifact_sha256,
            },
        )
        db.commit()
    return response
