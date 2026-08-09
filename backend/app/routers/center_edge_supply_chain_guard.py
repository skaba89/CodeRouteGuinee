from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.deps import require_roles
from app.edge_release import decode_release_scope, supply_chain_ready
from app.models_user import User
from app.routers.center_edge_release import EdgeReleaseRolloutUpdate, _release_by_id
from app.routers.center_edge_release_guard import guarded_release_rollout as _guarded_release_rollout

router = APIRouter(tags=["center-edge-supply-chain-guard"])


@router.post("/releases/{release_id}/rollout")
def supply_chain_guarded_rollout(
    release_id: str,
    payload: EdgeReleaseRolloutUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("super_admin")),
) -> dict:
    target = payload.rollout_status.strip().lower()
    if target in {"canary", "rolling", "released"}:
        release = _release_by_id(db, release_id, lock=True)
        if not release:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Edge release not found")
        scope = decode_release_scope(release.scope)
        manifest = scope.get("manifest") if isinstance(scope.get("manifest"), dict) else {}
        if not supply_chain_ready(manifest):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "code": "EDGE_SUPPLY_CHAIN_EVIDENCE_REQUIRED",
                    "message": (
                        "Le rollout est bloqué : provenance GitHub, SBOM, digest du sujet et scan de vulnérabilités "
                        "doivent être attachés au manifeste signé avant le canary."
                    ),
                },
            )
    return _guarded_release_rollout(release_id, payload, db, current_user)
