from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.edge_install_authorization import sign_install_authorization
from app.routers.center_edge_release import EdgeReleaseCheckRequest, check_edge_release as _check_edge_release

router = APIRouter(tags=["center-edge-install-authorization"])


@router.post("/release/check")
def authorized_edge_release_check(
    payload: EdgeReleaseCheckRequest,
    db: Session = Depends(get_db),
) -> dict:
    response = _check_edge_release(payload, db)
    if not response.get("update_available"):
        return response

    bundle = response.get("release") if isinstance(response.get("release"), dict) else {}
    manifest = bundle.get("manifest") if isinstance(bundle.get("manifest"), dict) else {}
    artifact = manifest.get("artifact") if isinstance(manifest.get("artifact"), dict) else {}
    response["install_authorization"] = sign_install_authorization(
        release_id=str(bundle.get("release_id") or manifest.get("release_id") or ""),
        source_release_id=str(response.get("source_release_id") or "") or None,
        node_id=payload.node_id,
        center_id=payload.center_id,
        action=str(response.get("action") or "install"),
        current_version=payload.current_version,
        software_version=str(manifest.get("software_version") or ""),
        artifact_sha256=str(artifact.get("sha256") or ""),
    )
    return response
