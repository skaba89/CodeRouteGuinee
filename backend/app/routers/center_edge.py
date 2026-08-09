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
    EDGE_REQUIRED_CAPABILITIES,
    EDGE_TARGET_SOFTWARE_VERSION,
    build_edge_scope,
    decode_edge_scope,
    encode_edge_scope,
    heartbeat_signing_payload,
    node_is_online,
    normalize_capabilities,
    normalize_heartbeat_telemetry,
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


class EdgeHeartbeatTelemetry(BaseModel):
    active_leases: int = Field(default=0, ge=0, le=100_000)
    finalized_leases: int = Field(default=0, ge=0, le=100_000)
    synced_leases: int = Field(default=0, ge=0, le=10_000_000)
    sync_pending: int = Field(default=0, ge=0, le=100_000)
    revalidation_required: int = Field(default=0, ge=0, le=100_000)
    corrupt_leases: int = Field(default=0, ge=0, le=100_000)
    media_files: int = Field(default=0, ge=0, le=1_000_000)
    media_bytes: int = Field(default=0, ge=0, le=10_000_000_000_000)


class EdgeHeartbeat(BaseModel):
    node_id: str
    center_id: str
    sequence: int = Field(ge=1)
    sent_at: datetime
    software_version: str = Field(min_length=1, max_length=80)
    capabilities: list[str] = Field(default_factory=list, max_length=32)
    telemetry: EdgeHeartbeatTelemetry | None = None
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


def _node_health(node: dict) -> dict:
    alerts: list[dict[str, str]] = []
    score = 100
    status_value = str(node.get("status") or "unknown")

    if status_value == "revoked":
        return {
            "health_score": 0,
            "health_status": "critical",
            "alerts": [{"code": "EDGE_REVOKED", "severity": "critical", "message": "Identité Edge révoquée."}],
            "version_drift": True,
            "missing_capabilities": list(EDGE_REQUIRED_CAPABILITIES),
        }
    if status_value == "suspended":
        score -= 65
        alerts.append({"code": "EDGE_SUSPENDED", "severity": "critical", "message": "Gateway suspendu par la DNTT."})

    if status_value == "active" and not node.get("online"):
        score -= 50
        alerts.append({"code": "EDGE_OFFLINE", "severity": "critical", "message": "Aucun heartbeat récent du gateway."})

    software_version = str(node.get("software_version") or "")
    version_drift = software_version != EDGE_TARGET_SOFTWARE_VERSION
    if version_drift:
        score -= 10
        alerts.append({
            "code": "EDGE_VERSION_DRIFT",
            "severity": "warning",
            "message": f"Version {software_version or 'inconnue'} ; cible {EDGE_TARGET_SOFTWARE_VERSION}.",
        })

    capabilities = set(normalize_capabilities(node.get("capabilities") or []))
    missing_capabilities = [value for value in EDGE_REQUIRED_CAPABILITIES if value not in capabilities]
    if missing_capabilities:
        score -= 15
        alerts.append({
            "code": "EDGE_CAPABILITY_DRIFT",
            "severity": "warning",
            "message": "Capacités manquantes : " + ", ".join(missing_capabilities),
        })

    telemetry = node.get("telemetry") if isinstance(node.get("telemetry"), dict) else None
    if telemetry is None:
        score -= 15
        alerts.append({"code": "EDGE_TELEMETRY_MISSING", "severity": "warning", "message": "Télémétrie P7 non reçue."})
    else:
        sync_pending = int(telemetry.get("sync_pending") or 0)
        revalidation = int(telemetry.get("revalidation_required") or 0)
        corrupt = int(telemetry.get("corrupt_leases") or 0)
        if sync_pending > 0:
            score -= min(25, 5 + sync_pending * 2)
            alerts.append({
                "code": "EDGE_SYNC_BACKLOG",
                "severity": "critical" if sync_pending >= 10 else "warning",
                "message": f"{sync_pending} tentative(s) finalisée(s) en attente de synchronisation.",
            })
        if revalidation > 0:
            score -= 20
            alerts.append({
                "code": "EDGE_REVALIDATION_REQUIRED",
                "severity": "critical",
                "message": f"{revalidation} tentative(s) active(s) nécessitent une revalidation après reboot.",
            })
        if corrupt > 0:
            score -= 30
            alerts.append({
                "code": "EDGE_LOCAL_CORRUPTION",
                "severity": "critical",
                "message": f"{corrupt} lease(s) local(aux) illisible(s).",
            })

    skew = float(node.get("clock_skew_seconds") or 0)
    if skew > 180:
        score -= 20
        alerts.append({"code": "EDGE_CLOCK_DRIFT", "severity": "critical", "message": f"Dérive horloge {round(skew, 1)} s."})
    elif skew > 60:
        score -= 10
        alerts.append({"code": "EDGE_CLOCK_DRIFT", "severity": "warning", "message": f"Dérive horloge {round(skew, 1)} s."})

    score = max(0, min(100, score))
    health_status = "healthy" if score >= 85 else "degraded" if score >= 60 else "critical"
    return {
        "health_score": score,
        "health_status": health_status,
        "alerts": alerts,
        "version_drift": version_drift,
        "missing_capabilities": missing_capabilities,
    }


def _node_read(authorization: InstitutionalAuthorization) -> dict:
    try:
        scope = decode_edge_scope(authorization.scope)
    except ValueError:
        scope = {"node_id": authorization.id, "kind": "invalid"}
    telemetry = normalize_heartbeat_telemetry(scope.get("last_telemetry"))
    node = {
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
        "telemetry": telemetry,
        "telemetry_at": scope.get("last_telemetry_at"),
        "created_at": authorization.created_at.isoformat() if authorization.created_at else None,
    }
    node.update(_node_health(node))
    return node


@router.get("/time")
def edge_server_time() -> dict:
    now = datetime.now(UTC)
    return {
        "server_time": now.isoformat().replace("+00:00", "Z"),
        "heartbeat_interval_seconds": EDGE_HEARTBEAT_INTERVAL_SECONDS,
        "max_clock_skew_seconds": EDGE_HEARTBEAT_MAX_SKEW_SECONDS,
        "target_software_version": EDGE_TARGET_SOFTWARE_VERSION,
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

    telemetry = normalize_heartbeat_telemetry(payload.telemetry.model_dump() if payload.telemetry else None)
    signing_payload = heartbeat_signing_payload(
        node_id=payload.node_id,
        center_id=payload.center_id,
        sequence=payload.sequence,
        sent_at=payload.sent_at,
        software_version=payload.software_version,
        capabilities=payload.capabilities,
        telemetry=telemetry,
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
    if telemetry is not None:
        scope["last_telemetry"] = telemetry
        scope["last_telemetry_at"] = now.isoformat().replace("+00:00", "Z")
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
        "target_software_version": EDGE_TARGET_SOFTWARE_VERSION,
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


@router.get("/fleet")
def edge_national_fleet(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "super_admin")),
) -> dict:
    del current_user
    nodes = [_node_read(item) for item in _all_edge_authorizations(db)]
    operational_centers = list(db.scalars(
        select(Center)
        .where(Center.status.in_(["active", "accredited"]))
        .order_by(Center.city.asc(), Center.name.asc())
    ).all())

    centers: list[dict] = []
    for center in operational_centers:
        center_nodes = [node for node in nodes if node.get("center_id") == center.id]
        online_nodes = [node for node in center_nodes if node.get("status") == "active" and node.get("online")]
        sync_pending = sum(int((node.get("telemetry") or {}).get("sync_pending") or 0) for node in center_nodes)
        revalidation = sum(int((node.get("telemetry") or {}).get("revalidation_required") or 0) for node in center_nodes)
        corrupt = sum(int((node.get("telemetry") or {}).get("corrupt_leases") or 0) for node in center_nodes)
        if not center_nodes:
            center_score = 0
            center_status = "critical"
            center_alerts = ["Aucun gateway Edge enrôlé"]
        else:
            center_score = round(sum(int(node.get("health_score") or 0) for node in center_nodes) / len(center_nodes))
            center_status = "critical" if not online_nodes or center_score < 60 else "degraded" if center_score < 85 else "healthy"
            center_alerts = []
            if not online_nodes:
                center_alerts.append("Aucun gateway Edge en ligne")
            if sync_pending:
                center_alerts.append(f"{sync_pending} synchronisation(s) en attente")
            if revalidation:
                center_alerts.append(f"{revalidation} revalidation(s) requise(s)")
            if corrupt:
                center_alerts.append(f"{corrupt} lease(s) corrompu(s)")
        centers.append({
            "center_id": center.id,
            "code": center.code,
            "name": center.name,
            "city": center.city,
            "health_score": center_score,
            "health_status": center_status,
            "node_count": len(center_nodes),
            "online_nodes": len(online_nodes),
            "sync_pending": sync_pending,
            "revalidation_required": revalidation,
            "corrupt_leases": corrupt,
            "version_drift_nodes": sum(1 for node in center_nodes if node.get("version_drift")),
            "alerts": center_alerts,
        })

    critical_centers = sum(1 for center in centers if center["health_status"] == "critical")
    degraded_centers = sum(1 for center in centers if center["health_status"] == "degraded")
    healthy_centers = sum(1 for center in centers if center["health_status"] == "healthy")
    version_drift_nodes = sum(1 for node in nodes if node.get("version_drift"))
    capability_drift_nodes = sum(1 for node in nodes if node.get("missing_capabilities"))
    upgrade_required_nodes = sum(
        1 for node in nodes
        if node.get("status") == "active" and (
            node.get("version_drift") or node.get("missing_capabilities")
        )
    )
    blocked_nodes = sum(
        1 for node in nodes
        if node.get("status") != "active" or node.get("health_status") == "critical"
    )

    national_status = "critical" if critical_centers else "degraded" if degraded_centers or version_drift_nodes else "healthy"
    return {
        "generated_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "status": national_status,
        "target_software_version": EDGE_TARGET_SOFTWARE_VERSION,
        "required_capabilities": list(EDGE_REQUIRED_CAPABILITIES),
        "summary": {
            "centers_total": len(centers),
            "centers_healthy": healthy_centers,
            "centers_degraded": degraded_centers,
            "centers_critical": critical_centers,
            "centers_without_gateway": sum(1 for center in centers if center["node_count"] == 0),
            "nodes_total": len(nodes),
            "nodes_active": sum(1 for node in nodes if node.get("status") == "active"),
            "nodes_online": sum(1 for node in nodes if node.get("online")),
            "sync_pending": sum(int((node.get("telemetry") or {}).get("sync_pending") or 0) for node in nodes),
            "revalidation_required": sum(int((node.get("telemetry") or {}).get("revalidation_required") or 0) for node in nodes),
            "corrupt_leases": sum(int((node.get("telemetry") or {}).get("corrupt_leases") or 0) for node in nodes),
            "version_drift_nodes": version_drift_nodes,
            "capability_drift_nodes": capability_drift_nodes,
        },
        "rollout": {
            "target_version": EDGE_TARGET_SOFTWARE_VERSION,
            "compliant_nodes": sum(
                1 for node in nodes
                if node.get("status") == "active" and not node.get("version_drift") and not node.get("missing_capabilities")
            ),
            "upgrade_required_nodes": upgrade_required_nodes,
            "blocked_nodes": blocked_nodes,
        },
        "centers": centers,
        "nodes": nodes,
    }
