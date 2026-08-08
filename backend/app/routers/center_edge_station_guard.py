from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit_chain import append_audit
from app.db.session import get_db
from app.edge_offline import (
    decode_lease_scope,
    encode_lease_scope,
    lease_signing_key_id,
    sign_lease_payload,
)
from app.models_center_station import CenterStation
from app.models_device_session import DeviceSession
from app.models_institutional_authorization import InstitutionalAuthorization
from app.routers.center_edge_offline import (
    EDGE_LEASE_AUTHORITY,
    EdgeLeaseIssueRequest,
    EdgeOfflineSyncRequest,
    issue_edge_lease as _issue_edge_lease,
    sync_edge_offline_submission as _sync_edge_offline_submission,
)

router = APIRouter(tags=["center-edge-offline"])


def _resolve_station_binding(
    db: Session,
    *,
    attempt_id: str,
    center_id: str,
    lock: bool = False,
) -> tuple[DeviceSession, CenterStation]:
    query = select(DeviceSession).where(
        DeviceSession.attempt_id == attempt_id,
        DeviceSession.center_id == center_id,
        DeviceSession.status == "active",
    ).order_by(DeviceSession.created_at.desc())
    if lock:
        query = query.with_for_update()
    device_sessions = list(db.scalars(query).all())
    if not device_sessions:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "EDGE_DEVICE_SESSION_REQUIRED",
                "message": "Le mode hors ligne exige une session de poste active liée à cette tentative.",
            },
        )

    distinct_keys = {session.device_key for session in device_sessions}
    if len(distinct_keys) != 1:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "EDGE_DEVICE_SESSION_AMBIGUOUS",
                "message": "Plusieurs postes actifs sont associés à la tentative. Une décision centre est requise.",
                "device_keys": sorted(distinct_keys),
            },
        )
    device_session = device_sessions[0]

    station_query = select(CenterStation).where(
        CenterStation.center_id == center_id,
        CenterStation.device_key == device_session.device_key,
    )
    if lock:
        station_query = station_query.with_for_update()
    stations = list(db.scalars(station_query).all())
    if not stations:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "EDGE_REGISTERED_STATION_REQUIRED",
                "message": "Le poste de cette tentative doit être enrôlé dans le registre du centre avant un lease hors ligne.",
                "device_key": device_session.device_key,
            },
        )
    active_stations = [station for station in stations if station.status == "active"]
    if not active_stations:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "EDGE_STATION_NOT_ACTIVE",
                "message": "Le poste enregistré n'est pas actif pour le mode hors ligne.",
                "station_statuses": sorted({station.status for station in stations}),
            },
        )
    if len(active_stations) != 1:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "EDGE_STATION_REGISTRY_AMBIGUOUS",
                "message": "Plusieurs postes actifs portent le même device_key dans ce centre. Le registre doit être corrigé.",
                "center_station_ids": sorted(station.id for station in active_stations),
            },
        )
    return device_session, active_stations[0]


def _binding_dict(device_session: DeviceSession, station: CenterStation) -> dict:
    return {
        "center_station_id": station.id,
        "device_session_id": device_session.id,
        "device_key": station.device_key,
        "label": station.label,
        "room": station.room,
    }


def _load_lease(db: Session, lease_id: str, *, lock: bool) -> InstitutionalAuthorization:
    query = select(InstitutionalAuthorization).where(
        InstitutionalAuthorization.id == lease_id,
        InstitutionalAuthorization.authority == EDGE_LEASE_AUTHORITY,
    )
    if lock:
        query = query.with_for_update()
    authorization = db.scalar(query)
    if not authorization:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Edge lease not found")
    return authorization


def _bind_lease_to_station(
    db: Session,
    *,
    lease_id: str,
    device_session: DeviceSession,
    station: CenterStation,
) -> dict:
    authorization = _load_lease(db, lease_id, lock=True)
    try:
        scope = decode_lease_scope(authorization.scope)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    binding = _binding_dict(device_session, station)
    existing = scope.get("station_binding")
    if existing and existing != binding:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "EDGE_LEASE_STATION_BINDING_CONFLICT",
                "message": "Le lease est déjà lié à un autre poste.",
            },
        )

    lease_payload = dict(scope.get("lease_payload") or {})
    if lease_payload.get("station") != binding:
        lease_payload["station"] = binding
        try:
            lease_hash, signature, key_id = sign_lease_payload(lease_payload)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={"code": "EDGE_LEASE_SIGNING_NOT_CONFIGURED", "message": str(exc)},
            ) from exc
        scope["lease_payload"] = lease_payload
        scope["lease_hash"] = lease_hash
        scope["lease_signature_b64"] = signature
        scope["signing_key_id"] = key_id
        scope["station_binding"] = binding
        authorization.scope = encode_lease_scope(scope)
        db.add(authorization)
        append_audit(
            db,
            actor_id=None,
            action="center_edge.lease_station_bound",
            entity="center_edge_exam_lease",
            entity_id=lease_id,
            details={
                "attempt_id": scope.get("attempt_id"),
                "center_id": scope.get("center_id"),
                **binding,
                "signing_key_id": lease_signing_key_id(),
            },
        )
        db.commit()
        db.refresh(authorization)
        scope = decode_lease_scope(authorization.scope)

    return {
        "lease": scope["lease_payload"],
        "lease_hash": scope["lease_hash"],
        "lease_signature_b64": scope["lease_signature_b64"],
        "signing_key_id": scope["signing_key_id"],
        "status": authorization.status,
    }


def _assert_bound_station_still_trusted(db: Session, scope: dict) -> None:
    binding = scope.get("station_binding")
    if not isinstance(binding, dict):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "EDGE_LEASE_STATION_BINDING_MISSING",
                "message": "Ce lease historique n'est pas lié cryptographiquement à un poste. Une revue d'incident est requise.",
            },
        )

    device_session = db.scalar(
        select(DeviceSession)
        .where(DeviceSession.id == binding.get("device_session_id"))
        .with_for_update()
    )
    station = db.scalar(
        select(CenterStation)
        .where(CenterStation.id == binding.get("center_station_id"))
        .with_for_update()
    )
    if not device_session or not station:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "EDGE_BOUND_STATION_MISSING", "message": "Le poste lié au lease est introuvable."},
        )
    if (
        device_session.status != "active"
        or device_session.attempt_id != scope.get("attempt_id")
        or device_session.center_id != scope.get("center_id")
        or device_session.device_key != binding.get("device_key")
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "EDGE_DEVICE_SESSION_NOT_TRUSTED",
                "message": "La session du poste n'est plus active ou ne correspond plus au lease.",
                "device_session_status": device_session.status,
            },
        )
    if (
        station.status != "active"
        or station.center_id != scope.get("center_id")
        or station.device_key != binding.get("device_key")
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "EDGE_STATION_REVOKED_AFTER_LEASE",
                "message": "Le poste a été désactivé ou modifié depuis l'émission du lease. Synchronisation automatique bloquée.",
                "station_status": station.status,
            },
        )


@router.post("/leases/issue", status_code=status.HTTP_201_CREATED)
def issue_edge_lease_bound_to_station(
    payload: EdgeLeaseIssueRequest,
    db: Session = Depends(get_db),
) -> dict:
    before_device, before_station = _resolve_station_binding(
        db,
        attempt_id=payload.attempt_id,
        center_id=payload.center_id,
        lock=True,
    )
    result = _issue_edge_lease(payload, db)

    # L'implémentation historique committe l'émission ; on reverrouille donc
    # explicitement le registre avant de signer le binding final.
    device_session, station = _resolve_station_binding(
        db,
        attempt_id=payload.attempt_id,
        center_id=payload.center_id,
        lock=True,
    )
    if device_session.id != before_device.id or station.id != before_station.id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "EDGE_STATION_CHANGED_DURING_LEASE_ISSUE",
                "message": "Le poste a changé pendant l'émission du lease. Recommencez l'activation Edge.",
            },
        )
    return _bind_lease_to_station(
        db,
        lease_id=str(result["lease"]["lease_id"]),
        device_session=device_session,
        station=station,
    )


@router.post("/offline-sync")
def sync_edge_offline_submission_bound_to_station(
    payload: EdgeOfflineSyncRequest,
    db: Session = Depends(get_db),
) -> dict:
    authorization = _load_lease(db, payload.lease_id, lock=True)
    try:
        scope = decode_lease_scope(authorization.scope)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    # Une fois le résultat central accepté, les retries réseau idempotents ne
    # dépendent plus de l'état ultérieur du poste.
    if authorization.status != "synced":
        _assert_bound_station_still_trusted(db, scope)
    return _sync_edge_offline_submission(payload, db)
