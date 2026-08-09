from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.audit_chain import append_audit
from app.db.session import get_db
from app.deps import require_roles
from app.edge_release import (
    decode_release_scope,
    encode_release_scope,
    normalize_supply_chain_evidence,
    release_signing_key_id,
    release_signing_public_key_b64,
    release_trusted_public_keys,
    sign_release_manifest,
    supply_chain_ready,
)
from app.models_user import User
from app.routers.center_edge_release import _public_release, _release_by_id

router = APIRouter(tags=["center-edge-supply-chain"])


class EdgeSupplyChainEvidence(BaseModel):
    builder: str = Field(default="github-actions", min_length=2, max_length=120)
    source_commit_sha: str = Field(min_length=40, max_length=64)
    workflow_ref: str = Field(min_length=3, max_length=500)
    provenance_url: str = Field(min_length=10, max_length=2000)
    sbom_sha256: str = Field(min_length=64, max_length=64)
    sbom_attestation_url: str | None = Field(default=None, max_length=2000)
    subject_sha256: str = Field(min_length=64, max_length=64)
    vulnerability_scan_status: str = Field(min_length=4, max_length=20)


@router.get("/release-signing-key")
def get_rotatable_release_signing_key() -> dict[str, Any]:
    """Retourne la clé active et le trousseau de transition P9.

    Les anciens agents P8 continuent à lire `key_id` et `public_key_b64`. Les
    agents P9 utilisent `trusted_keys` afin d'accepter temporairement une release
    signée avant rotation sans accepter indéfiniment une clé retirée.
    """
    try:
        return {
            "algorithm": "Ed25519",
            "key_id": release_signing_key_id(),
            "public_key_b64": release_signing_public_key_b64(),
            "trusted_keys": release_trusted_public_keys(),
        }
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "EDGE_RELEASE_SIGNING_NOT_CONFIGURED", "message": str(exc)},
        ) from exc


@router.post("/releases/{release_id}/supply-chain")
def attach_release_supply_chain_evidence(
    release_id: str,
    payload: EdgeSupplyChainEvidence,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("super_admin")),
) -> dict:
    item = _release_by_id(db, release_id, lock=True)
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Edge release not found")
    if item.status not in {"draft", "paused"}:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "EDGE_SUPPLY_CHAIN_IMMUTABLE_AFTER_ROLLOUT",
                "message": "Les preuves de build ne peuvent être modifiées qu'avant rollout ou pendant une pause explicite.",
            },
        )

    scope = decode_release_scope(item.scope)
    manifest = dict(scope.get("manifest") or {})
    artifact = manifest.get("artifact") if isinstance(manifest.get("artifact"), dict) else {}
    try:
        evidence = normalize_supply_chain_evidence(
            payload.model_dump(),
            artifact_sha256=str(artifact.get("sha256") or ""),
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    manifest["version"] = 2
    manifest["supply_chain"] = evidence
    manifest_hash, signature, key_id = sign_release_manifest(manifest)
    scope["manifest"] = manifest
    scope["manifest_hash"] = manifest_hash
    scope["manifest_signature_b64"] = signature
    scope["signing_key_id"] = key_id
    scope["supply_chain_attached_at"] = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    scope["supply_chain_attached_by_id"] = current_user.id
    item.scope = encode_release_scope(scope)
    item.updated_at = datetime.now(UTC).replace(tzinfo=None)
    db.add(item)
    append_audit(
        db,
        actor_id=current_user.id,
        action="center_edge.release_supply_chain_attached",
        entity="center_edge_release",
        entity_id=item.id,
        details={
            "software_version": manifest.get("software_version"),
            "source_commit_sha": evidence.get("source_commit_sha") if evidence else None,
            "sbom_sha256": evidence.get("sbom_sha256") if evidence else None,
            "subject_sha256": evidence.get("subject_sha256") if evidence else None,
            "vulnerability_scan_status": evidence.get("vulnerability_scan_status") if evidence else None,
            "provenance_url": evidence.get("provenance_url") if evidence else None,
            "signing_key_id": key_id,
        },
    )
    db.commit()
    db.refresh(item)
    response = _public_release(item)
    response["supply_chain_ready"] = supply_chain_ready(manifest)
    return response
