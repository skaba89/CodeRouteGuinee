from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit_chain import append_audit
from app.db.session import get_db
from app.deps import require_roles
from app.edge_gateway import (
    EDGE_AUTHORITY,
    EDGE_HEARTBEAT_INTERVAL_SECONDS,
    EDGE_HEARTBEAT_MAX_SKEW_SECONDS,
    build_edge_scope,
    decode_edge_scope,
    encode_edge_scope,
    heartbeat_signing_payload,
    node_is_online,
    normalize_capabilities,
    normalize_public_key_b64,
    public_key_fingerprint,
    verify_edge_signature,
)
from app.models_center import Center
from app.models_institutional_authorization import InstitutionalAuthorization
from app.models_user import User

router = APIRouter(prefix="/center-edge", tags=["center-edge"])


class EdgeNodeEnroll(BaseModel):
    center_id: str
    label: str = Field(min_length=3, max_length=120)
    public_key_b64: str = Field(min_length=40, max_length=80)
    capabilities: list[str] = Field(default_factory=list, max_length=32)


class EdgeNodeStatusUpdate(BaseModel):
    status: str
    reason: str = Field(min_length=3, max_length=500)


class EdgeHeartbeat(BaseModel):
    node_id: str
    center_id: str
    sequence: int = Field(ge=1)
    sent_at: datetime
    software_version: str = Field(min_length=1, max_length=80)
    capabilities: list[str] = Field(default_factory=list, max_length=32)
    signature_b64: str = Field(min_length=80, max_length=120)


def _load_edge_authorization(
    db: Session,
    node_id: str,
    *,
    lock: bool = False,
) -> InstitutionalAuthorization | None:
    query = select(InstitutionalAuthorization).where(
        InstitutionalAuthorization.id == node_id,
        InstitutionalAuthorization.authority == EDGE_AUTHORITY,
    )
    if lock:
        query = query.with_for_update()
    return db.scalar(query)


def _all_edge_authorizations(db: Session) -> list[InstitutionalAuthorization]:
    return list(db.scalars(
        select(InstitutionalAuthorization)
        .where(InstitutionalAuthorization.authority == EDGE_AUTHORITY)
        .order_by(InstitutionalAuthorization.created_at.desc())
    ).all())


def _assert_center_scope(current_user: User, center_id: str) -> None:
    if current_user.role != "center":
        return
    if current_user.center_id and current_user.center_id == center_id:
        return
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail={"code": "CENTER_SCOPE_MISMATCH", "message": "Ce gateway appartient à un autre centre."},
    )


def _node_read(authorization: InstitutionalAuthorization) -> dict:
    try:
        scope = decode_edge_scope(authorization.scope)
    except ValueError:
        scope = {"node_id": authorization.id, "kind": "invalid"}
    return {
        "node_id": authorization.id,
        "reference": authorization.reference,
        "center_id": scope.get("center_id"),
        "center_code": scope.get("center_code"),
        "label": scope.get("label"),
        "status": authorization.status,
        "online": authorization.status == "active" and node_is_online(scope),
        "public_key_fingerprint": scope.get("public_key_fingerprint"),
        "capabilities": scope.get("capabilities") or [],
        "last_sequence": int(scope.get("last_sequence") or 0),
        "last_seen_at": scope.get("last_seen_at"),
        "software_version": scope.get("last_software_version"),
        "clock_skew_seconds": scope.get("last_clock_skew_seconds"),
        "created_at": authorization.created_at.isoformat() if authorization.created_at else None,
    }


@router.get("/time")
def edge_server_time() -> dict:
    now = datetime.now(UTC)
    return {
        "server_time": now.isoformat().replace("+00:00", "Z"),
        "heartbeat_interval_seconds": EDGE_HEARTBEAT_INTERVAL_SECONDS,
        "max_clock_skew_seconds": EDGE_HEARTBEAT_MAX_SKEW_SECONDS,
    }


@router.post("/nodes", status_code=status.HTTP_201_CREATED)
def enroll_edge_node(
    payload: EdgeNodeEnroll,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "super_admin")),
) -> dict:
    center = db.get(Center, payload.center_id)
    if not center:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Center not found")
    if center.status not in {"active", "accredited"}:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "EDGE_CENTER_NOT_OPERATIONAL", "message": "Le centre doit être actif ou accrédité avant l'enrôlement Edge."},
        )

    try:
        normalized_key = normalize_public_key_b64(payload.public_key_b64)
        fingerprint = public_key_fingerprint(normalized_key)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    for existing in _all_edge_authorizations(db):
        try:
            existing_scope = decode_edge_scope(existing.scope)
        except ValueError:
            continue
        if existing_scope.get("public_key_fingerprint") == fingerprint:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "code": "EDGE_PUBLIC_KEY_ALREADY_ENROLLED",
                    "message": "Cette clé publique Edge est déjà enregistrée.",
                    "node_id": existing.id,
                },
            )

    node_id = str(uuid.uuid4())
    now = datetime.now(UTC)
    scope = build_edge_scope(
        node_id=node_id,
        center_id=center.id,
        center_code=center.code,
        label=payload.label,
        public_key_b64=normalized_key,
        capabilities=payload.capabilities,
        created_by_id=current_user.id,
        created_at=now,
    )
    reference = f"EDGE-{center.code}-{fingerprint[:12].upper()}"
    authorization = InstitutionalAuthorization(
        id=node_id,
        authority=EDGE_AUTHORITY,
        reference=reference,
        title=f"Gateway Edge — {payload.label.strip()[:120]}",
        scope=encode_edge_scope(scope),
        status="active",
        valid_from=now.replace(tzinfo=None),
        valid_until=None,
    )
    db.add(authorization)
    append_audit(
        db,
        actor_id=current_user.id,
        action="center_edge.node_enrolled",
        entity="center_edge_node",
        entity_id=node_id,
        details={
            "center_id": center.id,
            "center_code": center.code,
            "reference": reference,
            "label": payload.label,
            "public_key_fingerprint": fingerprint,
            "capabilities": normalize_capabilities(payload.capabilities),
        },
    )
    db.commit()
    db.refresh(authorization)
    return _node_read(authorization)


@router.get("/nodes")
def list_edge_nodes(
    center_id: str | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("center", "admin", "super_admin")),
) -> list[dict]:
    if current_user.role == "center":
        if not current_user.center_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Agent centre sans centre affecté")
        center_id = current_user.center_id

    nodes: list[dict] = []
    for authorization in _all_edge_authorizations(db):
        try:
            scope = decode_edge_scope(authorization.scope)
        except ValueError:
            continue
        if center_id and scope.get("center_id") != center_id:
            continue
        nodes.append(_node_read(authorization))
    return nodes


@router.post("/nodes/{node_id}/status")
def update_edge_node_status(
    node_id: str,
    payload: EdgeNodeStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "super_admin")),
) -> dict:
    target_status = payload.status.strip().lower()
    if target_status not in {"active", "suspended", "revoked"}:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Statut Edge invalide")

    authorization = _load_edge_authorization(db, node_id, lock=True)
    if not authorization:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Edge node not found")
    try:
        scope = decode_edge_scope(authorization.scope)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    previous_status = authorization.status
    if previous_status == "revoked" and target_status != "revoked":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "EDGE_REVOCATION_IS_FINAL", "message": "Une clé Edge révoquée doit être remplacée par un nouvel enrôlement."},
        )

    now = datetime.now(UTC)
    authorization.status = target_status
    authorization.updated_at = now.replace(tzinfo=None)
    authorization.valid_until = now.replace(tzinfo=None) if target_status == "revoked" else None
    scope["status_reason"] = payload.reason
    scope["status_updated_at"] = now.isoformat().replace("+00:00", "Z")
    scope["status_updated_by_id"] = current_user.id
    authorization.scope = encode_edge_scope(scope)
    db.add(authorization)
    append_audit(
        db,
        actor_id=current_user.id,
        action="center_edge.node_status_changed",
        entity="center_edge_node",
        entity_id=node_id,
        details={
            "center_id": scope.get("center_id"),
            "reference": authorization.reference,
            "previous_status": previous_status,
            "new_status": target_status,
            "reason": payload.reason,
            "public_key_fingerprint": scope.get("public_key_fingerprint"),
        },
    )
    db.commit()
    db.refresh(authorization)
    return _node_read(authorization)


@router.post("/heartbeat")
def edge_heartbeat(
    payload: EdgeHeartbeat,
    request: Request,
    db: Session = Depends(get_db),
) -> dict:
    authorization = _load_edge_authorization(db, payload.node_id, lock=True)
    if not authorization:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Edge node unknown")
    if authorization.status != "active":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Edge node is not active")

    try:
        scope = decode_edge_scope(authorization.scope)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Edge node identity invalid") from exc

    if scope.get("center_id") != payload.center_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Edge node center mismatch")

    signing_payload = heartbeat_signing_payload(
        node_id=payload.node_id,
        center_id=payload.center_id,
        sequence=payload.sequence,
        sent_at=payload.sent_at,
        software_version=payload.software_version,
        capabilities=payload.capabilities,
    )
    if not verify_edge_signature(
        str(scope.get("public_key_b64") or ""),
        signing_payload,
        payload.signature_b64,
    ):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Edge signature")

    now = datetime.now(UTC)
    sent_at = payload.sent_at if payload.sent_at.tzinfo else payload.sent_at.replace(tzinfo=UTC)
    sent_at = sent_at.astimezone(UTC)
    clock_skew = abs((now - sent_at).total_seconds())
    if clock_skew > EDGE_HEARTBEAT_MAX_SKEW_SECONDS:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "EDGE_CLOCK_SKEW_TOO_HIGH",
                "message": "L'horloge du gateway Edge doit être resynchronisée avant de traiter des examens hors ligne.",
                "clock_skew_seconds": round(clock_skew, 3),
                "max_clock_skew_seconds": EDGE_HEARTBEAT_MAX_SKEW_SECONDS,
            },
        )

    last_sequence = int(scope.get("last_sequence") or 0)
    if payload.sequence <= last_sequence:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "EDGE_HEARTBEAT_REPLAY",
                "message": "Heartbeat Edge déjà traité ou hors séquence.",
                "last_sequence": last_sequence,
                "received_sequence": payload.sequence,
            },
        )

    forwarded_for = request.headers.get("x-forwarded-for", "").split(",")[0].strip()
    observed_ip = forwarded_for or (request.client.host if request.client else None)
    scope["last_sequence"] = payload.sequence
    scope["last_seen_at"] = now.isoformat().replace("+00:00", "Z")
    scope["last_sent_at"] = sent_at.isoformat().replace("+00:00", "Z")
    scope["last_software_version"] = payload.software_version.strip()[:80]
    scope["last_clock_skew_seconds"] = round(clock_skew, 3)
    scope["capabilities"] = normalize_capabilities(payload.capabilities)
    scope["last_observed_ip"] = observed_ip
    authorization.scope = encode_edge_scope(scope)
    authorization.updated_at = now.replace(tzinfo=None)
    db.add(authorization)
    db.commit()

    return {
        "accepted": True,
        "node_id": payload.node_id,
        "center_id": payload.center_id,
        "sequence": payload.sequence,
        "server_time": now.isoformat().replace("+00:00", "Z"),
        "clock_skew_seconds": round(clock_skew, 3),
        "next_heartbeat_seconds": EDGE_HEARTBEAT_INTERVAL_SECONDS,
    }


@router.get("/readiness")
def edge_readiness(
    center_id: str | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("center", "admin", "super_admin")),
) -> dict:
    if current_user.role == "center":
        if not current_user.center_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Agent centre sans centre affecté")
        center_id = current_user.center_id

    nodes = list_edge_nodes(center_id=center_id, db=db, current_user=current_user)
    active = [node for node in nodes if node["status"] == "active"]
    online = [node for node in active if node["online"]]
    stale = [node for node in active if not node["online"]]
    return {
        "status": "ready" if active and not stale else "degraded",
        "center_id": center_id,
        "total_nodes": len(nodes),
        "active_nodes": len(active),
        "online_nodes": len(online),
        "stale_nodes": len(stale),
        "suspended_nodes": sum(1 for node in nodes if node["status"] == "suspended"),
        "revoked_nodes": sum(1 for node in nodes if node["status"] == "revoked"),
        "heartbeat_interval_seconds": EDGE_HEARTBEAT_INTERVAL_SECONDS,
        "nodes": nodes,
    }
