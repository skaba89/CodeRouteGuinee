from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.candidate_eligibility import assert_candidate_ready_for_official_exam
from app.db.session import get_db
from app.deps import require_roles
from app.entry_service import build_entry_denied, build_entry_success
from app.exam_center_gate import (
    assert_center_actor_scope,
    assert_checkin_window,
    require_operational_center,
)
from app.models_audit import AuditLog
from app.models_booking import Booking
from app.models_candidate import Candidate
from app.models_session import ExamSession
from app.models_user import User

router = APIRouter(prefix="/entries", tags=["entries"])


class EntryIn(BaseModel):
    reference: str
    verification_code: str
    center_code: str | None = None


def _record_entry_log(
    db: Session,
    reference: str,
    result: str,
    reason: str | None,
    center_code: str | None,
    *,
    actor_id: str | None = None,
    extra: dict | None = None,
) -> None:
    details = {
        "reference": reference,
        "result": result,
        "reason": reason,
        "center_code": center_code,
    }
    if extra:
        details.update(extra)
    db.add(
        AuditLog(
            actor_id=actor_id,
            action="entry_validation",
            entity="booking",
            details=details,
        )
    )


def _deny_entry(
    db: Session,
    payload: EntryIn,
    current_user: User,
    reason: str,
    *,
    extra: dict | None = None,
) -> dict:
    _record_entry_log(
        db,
        payload.reference,
        "denied",
        reason,
        payload.center_code,
        actor_id=current_user.id,
        extra=extra,
    )
    db.commit()
    result = build_entry_denied(payload.reference, reason)
    if extra:
        result["details"] = extra
    return result


def _gate_reason(exc: HTTPException) -> tuple[str, dict]:
    detail = exc.detail
    if isinstance(detail, dict):
        code = str(detail.get("code") or "center_gate_denied").lower()
        return code, detail
    return "center_gate_denied", {"message": str(detail)}


@router.post("/validate")
def validate_entry(
    payload: EntryIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("center", "admin", "super_admin")),
) -> dict:
    # Verrou transactionnel : deux scans simultanés ne peuvent pas valider deux
    # fois la même réservation sur PostgreSQL.
    booking = db.scalar(
        select(Booking)
        .where(Booking.reference == payload.reference)
        .with_for_update()
    )
    if not booking:
        return _deny_entry(db, payload, current_user, "booking_not_found")
    if booking.verification_code != payload.verification_code:
        return _deny_entry(db, payload, current_user, "invalid_verification_code")
    if booking.status == "checked_in":
        return _deny_entry(
            db,
            payload,
            current_user,
            "already_checked_in",
            extra={"session_id": booking.session_id},
        )

    session = db.get(ExamSession, booking.session_id)
    if not session:
        return _deny_entry(db, payload, current_user, "session_not_found")

    # Un agent de centre ne peut scanner que les convocations de son centre.
    # Cette violation est un 403 et non un simple résultat de scan négatif.
    assert_center_actor_scope(current_user, session)

    try:
        center = require_operational_center(db, session)
    except HTTPException as exc:
        reason, detail = _gate_reason(exc)
        return _deny_entry(db, payload, current_user, reason, extra=detail)

    if payload.center_code and payload.center_code.strip() != center.code:
        return _deny_entry(
            db,
            payload,
            current_user,
            "wrong_exam_center",
            extra={
                "expected_center_code": center.code,
                "provided_center_code": payload.center_code.strip(),
                "session_id": session.id,
            },
        )

    # Parcours standard national : le paiement doit être finalisé avant le
    # check-in. Les cas d'exonération devront utiliser un statut institutionnel
    # explicite plutôt qu'un contournement silencieux de cette règle.
    if booking.status != "paid":
        return _deny_entry(
            db,
            payload,
            current_user,
            "payment_required_before_checkin",
            extra={"booking_status": booking.status, "session_id": session.id},
        )

    candidate = db.get(Candidate, booking.candidate_id)
    if not candidate:
        return _deny_entry(
            db,
            payload,
            current_user,
            "candidate_not_found",
            extra={"candidate_id": booking.candidate_id, "session_id": session.id},
        )

    # Le contrôle physique ne se réduit pas au QR et au paiement : le dossier
    # doit aussi être éligible. Le refus est renvoyé comme résultat de scan
    # structuré afin que l'agent centre voie la cause sans transformer le scan
    # attendu en erreur technique HTTP.
    try:
        assert_candidate_ready_for_official_exam(candidate)
    except HTTPException as exc:
        reason, detail = _gate_reason(exc)
        return _deny_entry(db, payload, current_user, reason, extra=detail)

    try:
        window = assert_checkin_window(session)
    except HTTPException as exc:
        reason, detail = _gate_reason(exc)
        return _deny_entry(db, payload, current_user, reason, extra=detail)

    booking.status = "checked_in"
    db.add(booking)
    _record_entry_log(
        db,
        payload.reference,
        "allowed",
        None,
        center.code,
        actor_id=current_user.id,
        extra={
            "booking_id": booking.id,
            "candidate_id": booking.candidate_id,
            "candidate_status": candidate.status,
            "session_id": session.id,
            "center_id": center.id,
            "window_opens_at": window.opens_at.isoformat(),
            "window_closes_at": window.closes_at.isoformat(),
        },
    )
    db.commit()
    return build_entry_success(payload.reference, center.code)


@router.get("/summary")
def get_entry_summary(
    days: int = Query(default=90, ge=1, le=365),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "super_admin")),
) -> dict:
    """
    Statistiques des validations d'entrée.
    Bornée à `days` jours (défaut 90) et streaming par lots de 1000 —
    évite de charger des centaines de milliers de logs en RAM à l'échelle nationale.
    """
    from datetime import UTC, datetime, timedelta
    cutoff = datetime.now(UTC).replace(tzinfo=None) - timedelta(days=days)

    total = 0
    by_result: dict[str, int] = {}
    by_center: dict[str, dict[str, int]] = {}

    stream = db.scalars(
        select(AuditLog)
        .where(AuditLog.action == "entry_validation", AuditLog.created_at >= cutoff)
        .execution_options(yield_per=1000)
    )
    for log in stream:
        details = log.details or {}
        result = details.get("result", "unknown")
        center_code = details.get("center_code") or "unknown"
        total += 1
        by_result[result] = by_result.get(result, 0) + 1
        by_center.setdefault(center_code, {"allowed": 0, "denied": 0})
        if result in by_center[center_code]:
            by_center[center_code][result] += 1
    return {"total": total, "by_result": by_result, "by_center": by_center, "window_days": days}


@router.get("/logs")
def list_entry_logs(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "super_admin")),
) -> list[dict]:
    logs = db.scalars(
        select(AuditLog)
        .where(AuditLog.action == "entry_validation")
        .order_by(AuditLog.created_at.desc())
        .limit(100)
    ).all()
    return [
        {
            "id": log.id,
            "details": log.details,
            "created_at": log.created_at.isoformat(),
        }
        for log in logs
    ]
