from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit_chain import append_audit
from app.db.session import get_db
from app.deps import require_roles
from app.edge_gateway import EDGE_AUTHORITY, decode_edge_scope
from app.edge_release import (
    EDGE_RELEASE_ALLOWED_STATUSES,
    EDGE_RELEASE_ATTESTATION_AUTHORITY,
    EDGE_RELEASE_ATTESTATION_SCOPE_KIND,
    EDGE_RELEASE_AUTHORITY,
    EDGE_RELEASE_SCOPE_KIND,
    build_release_manifest,
    decode_attestation_scope,
    decode_release_scope,
    encode_attestation_scope,
    encode_release_scope,
    release_is_eligible,
    release_signing_key_id,
    release_signing_public_key_b64,
    sign_release_manifest,
)
from app.models_institutional_authorization import InstitutionalAuthorization
from app.models_user import User
from app.routers.center_edge_offline import _verify_node_action

router = APIRouter(tags=["center-edge-release"])


class EdgeReleaseCreate(BaseModel):
    software_version: str = Field(min_length=1, max_length=80)
    artifact_url: str = Field(min_length=10, max_length=2000)
    artifact_sha256: str = Field(min_length=64, max_length=64)
    artifact_size_bytes: int = Field(gt=0)
    min_current_version: str | None = Field(default=None, max_length=80)
    release_notes: str | None = Field(default=None, max_length=4000)
    canary_node_ids: list[str] = Field(default_factory=list, max_length=100)
    allowed_center_ids: list[str] = Field(default_factory=list, max_length=5000)
    rollback_release_id: str | None = None


class EdgeReleaseRolloutUpdate(BaseModel):
    rollout_status: str
    rollout_percent: int = Field(default=0, ge=0, le=100)
    canary_node_ids: list[str] | None = Field(default=None, max_length=100)
    allowed_center_ids: list[str] | None = Field(default=None, max_length=5000)
    rollback_release_id: str | None = None
    reason: str = Field(min_length=3, max_length=1000)


class EdgeReleaseCheckRequest(BaseModel):
    node_id: str
    center_id: str
    sequence: int = Field(ge=1)
    sent_at: datetime
    current_version: str = Field(min_length=1, max_length=80)
    signature_b64: str = Field(min_length=80, max_length=120)


class EdgeReleaseAttestationRequest(BaseModel):
    node_id: str
    center_id: str
    sequence: int = Field(ge=1)
    sent_at: datetime
    release_id: str
    software_version: str = Field(min_length=1, max_length=80)
    result: str = Field(min_length=3, max_length=40)
    artifact_sha256: str = Field(min_length=64, max_length=64)
    signature_b64: str = Field(min_length=80, max_length=120)


def _release_query():
    return select(InstitutionalAuthorization).where(
        InstitutionalAuthorization.authority == EDGE_RELEASE_AUTHORITY
    )


def _release_by_id(db: Session, release_id: str, *, lock: bool = False) -> InstitutionalAuthorization | None:
    query = _release_query().where(InstitutionalAuthorization.id == release_id)
    if lock:
        query = query.with_for_update()
    return db.scalar(query)


def _public_release(item: InstitutionalAuthorization) -> dict:
    scope = decode_release_scope(item.scope)
    return {
        "release_id": item.id,
        "reference": item.reference,
        "status": item.status,
        "rollout_status": scope.get("rollout_status"),
        "rollout_percent": int(scope.get("rollout_percent") or 0),
        "canary_node_ids": scope.get("canary_node_ids") or [],
        "allowed_center_ids": scope.get("allowed_center_ids") or [],
        "rollback_release_id": scope.get("rollback_release_id"),
        "manifest": scope["manifest"],
        "manifest_hash": scope["manifest_hash"],
        "manifest_signature_b64": scope["manifest_signature_b64"],
        "signing_key_id": scope["signing_key_id"],
        "created_at": item.created_at.isoformat() if item.created_at else None,
        "updated_at": item.updated_at.isoformat() if item.updated_at else None,
    }


def _release_bundle(item: InstitutionalAuthorization) -> dict:
    scope = decode_release_scope(item.scope)
    return {
        "release_id": item.id,
        "manifest": scope["manifest"],
        "manifest_hash": scope["manifest_hash"],
        "manifest_signature_b64": scope["manifest_signature_b64"],
        "signing_key_id": scope["signing_key_id"],
    }


def _attestations_for_release(db: Session, release_id: str) -> list[InstitutionalAuthorization]:
    return list(db.scalars(
        select(InstitutionalAuthorization)
        .where(InstitutionalAuthorization.authority == EDGE_RELEASE_ATTESTATION_AUTHORITY)
        .order_by(InstitutionalAuthorization.updated_at.desc(), InstitutionalAuthorization.created_at.desc())
    ).all())


@router.get("/release-signing-key")
def get_release_signing_key() -> dict:
    try:
        return {
            "algorithm": "Ed25519",
            "key_id": release_signing_key_id(),
            "public_key_b64": release_signing_public_key_b64(),
        }
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "EDGE_RELEASE_SIGNING_NOT_CONFIGURED", "message": str(exc)},
        ) from exc


@router.post("/releases", status_code=status.HTTP_201_CREATED)
def create_edge_release(
    payload: EdgeReleaseCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("super_admin")),
) -> dict:
    release_id = str(uuid.uuid4())
    now = datetime.now(UTC)
    try:
        manifest = build_release_manifest(
            release_id=release_id,
            software_version=payload.software_version,
            artifact_url=payload.artifact_url,
            artifact_sha256=payload.artifact_sha256,
            artifact_size_bytes=payload.artifact_size_bytes,
            created_at=now.isoformat().replace("+00:00", "Z"),
            min_current_version=payload.min_current_version,
            release_notes=payload.release_notes,
        )
        manifest_hash, signature, key_id = sign_release_manifest(manifest)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    if payload.rollback_release_id and not _release_by_id(db, payload.rollback_release_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rollback release not found")

    scope = {
        "kind": EDGE_RELEASE_SCOPE_KIND,
        "release_id": release_id,
        "manifest": manifest,
        "manifest_hash": manifest_hash,
        "manifest_signature_b64": signature,
        "signing_key_id": key_id,
        "rollout_status": "draft",
        "rollout_percent": 0,
        "canary_node_ids": sorted(set(payload.canary_node_ids)),
        "allowed_center_ids": sorted(set(payload.allowed_center_ids)),
        "rollback_release_id": payload.rollback_release_id,
        "created_by_id": current_user.id,
        "last_rollout_reason": "Création de la release",
    }
    item = InstitutionalAuthorization(
        id=release_id,
        authority=EDGE_RELEASE_AUTHORITY,
        reference=f"EDGEREL-{payload.software_version.strip()}-{release_id[:8]}",
        title=f"Release Center Edge {payload.software_version.strip()}",
        scope=encode_release_scope(scope),
        status="draft",
        valid_from=None,
        valid_until=None,
    )
    db.add(item)
    append_audit(
        db,
        actor_id=current_user.id,
        action="center_edge.release_created",
        entity="center_edge_release",
        entity_id=release_id,
        details={
            "software_version": manifest["software_version"],
            "artifact_sha256": manifest["artifact"]["sha256"],
            "artifact_size_bytes": manifest["artifact"]["size_bytes"],
            "signing_key_id": key_id,
        },
    )
    db.commit()
    db.refresh(item)
    return _public_release(item)


@router.get("/releases")
def list_edge_releases(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "super_admin")),
) -> list[dict]:
    del current_user
    items = list(db.scalars(_release_query().order_by(InstitutionalAuthorization.created_at.desc())).all())
    return [_public_release(item) for item in items]


@router.post("/releases/{release_id}/rollout")
def update_release_rollout(
    release_id: str,
    payload: EdgeReleaseRolloutUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("super_admin")),
) -> dict:
    target = payload.rollout_status.strip().lower()
    if target not in EDGE_RELEASE_ALLOWED_STATUSES:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Statut de rollout Edge invalide")
    item = _release_by_id(db, release_id, lock=True)
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Edge release not found")
    scope = decode_release_scope(item.scope)
    previous = str(scope.get("rollout_status") or item.status)
    if previous == "revoked" and target != "revoked":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "EDGE_RELEASE_REVOCATION_FINAL", "message": "Une release révoquée ne peut pas être réactivée."},
        )
    if target == "canary" and not (payload.canary_node_ids or scope.get("canary_node_ids")):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Au moins un gateway canary est requis")
    if target == "rolling" and payload.rollout_percent <= 0:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Le rollout progressif doit être supérieur à 0%")

    rollback_release_id = payload.rollback_release_id or scope.get("rollback_release_id")
    if target == "rollback":
        if not rollback_release_id:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Une release de rollback est obligatoire")
        rollback = _release_by_id(db, str(rollback_release_id))
        if not rollback or rollback.id == item.id:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Release de rollback invalide")

    if payload.canary_node_ids is not None:
        scope["canary_node_ids"] = sorted(set(payload.canary_node_ids))
    if payload.allowed_center_ids is not None:
        scope["allowed_center_ids"] = sorted(set(payload.allowed_center_ids))
    scope["rollout_status"] = target
    scope["rollout_percent"] = 100 if target == "released" else int(payload.rollout_percent)
    scope["rollback_release_id"] = rollback_release_id
    scope["last_rollout_reason"] = payload.reason
    scope["last_rollout_by_id"] = current_user.id
    scope["last_rollout_at"] = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    item.scope = encode_release_scope(scope)
    item.status = target
    item.updated_at = datetime.now(UTC).replace(tzinfo=None)
    if target in {"canary", "rolling", "released"} and item.valid_from is None:
        item.valid_from = datetime.now(UTC).replace(tzinfo=None)
    db.add(item)
    append_audit(
        db,
        actor_id=current_user.id,
        action="center_edge.release_rollout_changed",
        entity="center_edge_release",
        entity_id=item.id,
        details={
            "previous_status": previous,
            "new_status": target,
            "rollout_percent": scope["rollout_percent"],
            "rollback_release_id": rollback_release_id,
            "reason": payload.reason,
        },
    )
    db.commit()
    db.refresh(item)
    return _public_release(item)


@router.post("/release/check")
def check_edge_release(
    payload: EdgeReleaseCheckRequest,
    db: Session = Depends(get_db),
) -> dict:
    node_authorization, _node_scope, _signed = _verify_node_action(
        db,
        action="release.check",
        node_id=payload.node_id,
        center_id=payload.center_id,
        sequence=payload.sequence,
        sent_at=payload.sent_at,
        fields={"current_version": payload.current_version.strip()},
        signature_b64=payload.signature_b64,
        require_recent_heartbeat=True,
    )

    releases = list(db.scalars(_release_query().order_by(InstitutionalAuthorization.created_at.desc())).all())
    for item in releases:
        scope = decode_release_scope(item.scope)
        if not release_is_eligible(scope, node_id=payload.node_id, center_id=payload.center_id):
            continue
        manifest = scope["manifest"]
        rollout_status = str(scope.get("rollout_status") or "draft")
        if rollout_status == "rollback":
            # Le rollback n'est proposé qu'aux nœuds réellement sur la version fautive.
            if payload.current_version.strip() != str(manifest.get("software_version") or ""):
                continue
            rollback_id = str(scope.get("rollback_release_id") or "")
            rollback_item = _release_by_id(db, rollback_id)
            if not rollback_item:
                continue
            db.add(node_authorization)
            db.commit()
            return {
                "update_available": True,
                "action": "rollback",
                "source_release_id": item.id,
                "release": _release_bundle(rollback_item),
            }
        if payload.current_version.strip() == str(manifest.get("software_version") or ""):
            continue
        db.add(node_authorization)
        db.commit()
        return {
            "update_available": True,
            "action": "install",
            "release": _release_bundle(item),
            "rollout_status": rollout_status,
        }

    db.add(node_authorization)
    db.commit()
    return {"update_available": False, "action": "none", "current_version": payload.current_version.strip()}


@router.post("/release/attest")
def attest_edge_release(
    payload: EdgeReleaseAttestationRequest,
    db: Session = Depends(get_db),
) -> dict:
    result = payload.result.strip().lower()
    if result not in {"staged", "installed", "failed", "rolled_back"}:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Résultat d'attestation invalide")
    release = _release_by_id(db, payload.release_id)
    if not release:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Edge release not found")
    release_scope = decode_release_scope(release.scope)
    expected_sha = str(release_scope["manifest"]["artifact"]["sha256"])
    if payload.artifact_sha256.strip().lower() != expected_sha:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="SHA-256 attesté différent du manifeste signé")

    fields = {
        "release_id": payload.release_id,
        "software_version": payload.software_version.strip(),
        "result": result,
        "artifact_sha256": expected_sha,
    }
    node_authorization, _node_scope, _signed = _verify_node_action(
        db,
        action="release.attest",
        node_id=payload.node_id,
        center_id=payload.center_id,
        sequence=payload.sequence,
        sent_at=payload.sent_at,
        fields=fields,
        signature_b64=payload.signature_b64,
        require_recent_heartbeat=False,
    )

    reference = f"EDGEATTEST-{payload.release_id}-{payload.node_id}"
    item = db.scalar(select(InstitutionalAuthorization).where(
        InstitutionalAuthorization.authority == EDGE_RELEASE_ATTESTATION_AUTHORITY,
        InstitutionalAuthorization.reference == reference,
    ).with_for_update())
    now = datetime.now(UTC)
    event = {
        "sequence": payload.sequence,
        "result": result,
        "software_version": payload.software_version.strip(),
        "artifact_sha256": expected_sha,
        "attested_at": now.isoformat().replace("+00:00", "Z"),
    }
    if item:
        scope = decode_attestation_scope(item.scope)
        history = list(scope.get("history") or [])[-19:]
        history.append(event)
        scope["history"] = history
        scope["last_event"] = event
        item.scope = encode_attestation_scope(scope)
        item.status = result
        item.updated_at = now.replace(tzinfo=None)
    else:
        scope = {
            "kind": EDGE_RELEASE_ATTESTATION_SCOPE_KIND,
            "release_id": payload.release_id,
            "node_id": payload.node_id,
            "center_id": payload.center_id,
            "history": [event],
            "last_event": event,
        }
        item = InstitutionalAuthorization(
            authority=EDGE_RELEASE_ATTESTATION_AUTHORITY,
            reference=reference,
            title=f"Attestation release {payload.release_id} / node {payload.node_id}",
            scope=encode_attestation_scope(scope),
            status=result,
            valid_from=now.replace(tzinfo=None),
        )
    db.add(item)
    db.add(node_authorization)
    append_audit(
        db,
        actor_id=None,
        action="center_edge.release_attested",
        entity="center_edge_release_attestation",
        entity_id=item.id,
        details={
            "release_id": payload.release_id,
            "node_id": payload.node_id,
            "center_id": payload.center_id,
            "software_version": payload.software_version.strip(),
            "result": result,
            "artifact_sha256": expected_sha,
        },
    )
    db.commit()
    db.refresh(item)
    return {"accepted": True, "attestation_id": item.id, "result": result}


@router.get("/releases/{release_id}/rollout")
def release_rollout_status(
    release_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "super_admin")),
) -> dict:
    del current_user
    release = _release_by_id(db, release_id)
    if not release:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Edge release not found")
    attestations: list[dict] = []
    counts = {"staged": 0, "installed": 0, "failed": 0, "rolled_back": 0}
    for item in _attestations_for_release(db, release_id):
        try:
            scope = decode_attestation_scope(item.scope)
        except ValueError:
            continue
        if scope.get("release_id") != release_id:
            continue
        last_event = scope.get("last_event") or {}
        result = str(last_event.get("result") or item.status)
        if result in counts:
            counts[result] += 1
        attestations.append({
            "attestation_id": item.id,
            "node_id": scope.get("node_id"),
            "center_id": scope.get("center_id"),
            "result": result,
            "software_version": last_event.get("software_version"),
            "attested_at": last_event.get("attested_at"),
        })

    nodes = list(db.scalars(select(InstitutionalAuthorization).where(
        InstitutionalAuthorization.authority == EDGE_AUTHORITY,
        InstitutionalAuthorization.status == "active",
    )).all())
    eligible = 0
    scope = decode_release_scope(release.scope)
    for node in nodes:
        try:
            node_scope = decode_edge_scope(node.scope)
        except ValueError:
            continue
        if release_is_eligible(scope, node_id=node.id, center_id=str(node_scope.get("center_id") or "")):
            eligible += 1

    return {
        "release": _public_release(release),
        "eligible_nodes": eligible,
        "attestation_counts": counts,
        "attestations": attestations,
    }
