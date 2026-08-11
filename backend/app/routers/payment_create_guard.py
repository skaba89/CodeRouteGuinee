from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.audit_chain import append_audit
from app.db.session import get_db
from app.deps import get_current_user
from app.models_audit import AuditLog
from app.models_booking import Booking
from app.models_candidate import Candidate
from app.models_payment import Payment
from app.models_user import User
from app.payment_rules import (
    acquire_payment_reference_lock,
    assert_booking_can_start_payment,
    assert_payment_amount,
    assert_payment_booking_access,
    normalize_payment_provider,
    resolve_authoritative_amount,
    synchronize_booking_from_payment,
)
from app.payment_service import build_payment_reference, build_receipt_number
from app.routers import payment_refunds
from app.routers import payments as legacy_payments
from app.routers.payments import PaymentIn

router = APIRouter(prefix="/payments", tags=["payments"])


def _payment_payload(payment: Payment, *, message: str) -> dict:
    return {
        "id": payment.id,
        "reference": payment.reference,
        "booking_reference": payment.booking_reference,
        "amount_gnf": payment.amount_gnf,
        "provider": payment.provider,
        "status": payment.status,
        "receipt_number": payment.receipt_number,
        "external_reference": payment.external_reference,
        "paid_at": payment.paid_at.isoformat() if payment.paid_at else None,
        "message": message,
        "checkout_url": payment.checkout_url or "",
    }


def _notify_payment_best_effort(db: Session, booking: Booking, payment: Payment) -> None:
    try:
        candidate = db.get(Candidate, booking.candidate_id)
        if candidate and candidate.email:
            from app.email_service import send_payment_confirmation

            send_payment_confirmation(
                to_email=candidate.email,
                candidate_name=f"{candidate.first_name} {candidate.last_name}",
                booking_reference=booking.reference,
                amount_gnf=payment.amount_gnf,
                provider=payment.provider,
                receipt_number=payment.receipt_number,
            )
    except Exception as exc:
        try:
            from app.sentry import capture_exception

            capture_exception(exc, context={"endpoint": "payment_email"})
        except Exception:
            pass


@router.post("", status_code=status.HTTP_201_CREATED)
def create_payment_idempotent(
    payload: PaymentIn,
    response: Response,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    # La réservation est la clé d'idempotence métier. Le verrou couvre le test
    # d'existence ET la création afin que deux doubles-clics concurrents ne
    # puissent jamais appeler deux fois le provider.
    booking = db.scalar(
        select(Booking)
        .where(Booking.reference == payload.booking_reference.strip())
        .with_for_update()
    )
    if not booking:
        db.add(
            AuditLog(
                actor_id=current_user.id,
                action="payment.failed",
                entity="payment",
                entity_id=payload.booking_reference,
                details={
                    "reason": "booking_not_found",
                    "booking_reference": payload.booking_reference,
                    "requested_amount_gnf": payload.amount_gnf,
                    "provider": payload.provider,
                },
            )
        )
        db.commit()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found")

    assert_payment_booking_access(db, current_user, booking)

    existing = db.scalar(
        select(Payment)
        .where(
            Payment.booking_reference == booking.reference,
            Payment.status.in_(["paid", "pending"]),
        )
        .order_by(Payment.created_at.desc())
        .limit(1)
    )
    if existing is not None:
        db.add(
            AuditLog(
                actor_id=current_user.id,
                action="payment.idempotent_replay",
                entity="payment",
                entity_id=existing.reference,
                details={
                    "booking_reference": booking.reference,
                    "payment_status": existing.status,
                    "provider": existing.provider,
                    "checkout_url_restored": bool(existing.checkout_url),
                },
            )
        )
        db.commit()
        response.status_code = status.HTTP_200_OK
        return _payment_payload(
            existing,
            message="Paiement existant récupéré sans nouveau débit.",
        )

    # Si la base dit déjà paid/checked_in mais qu'aucun paiement ouvert n'est
    # retrouvable, on préfère bloquer et rapprocher plutôt que risquer un débit
    # supplémentaire sur un dossier incohérent.
    assert_booking_can_start_payment(db, booking)

    authoritative_amount = resolve_authoritative_amount(db, booking)
    assert_payment_amount(payload.amount_gnf, authoritative_amount)
    provider = normalize_payment_provider(payload.provider)

    provider_result = legacy_payments.simulate_mobile_money_payment(
        provider, payload.phone, authoritative_amount
    )

    acquire_payment_reference_lock(db)
    reference = build_payment_reference(
        (db.scalar(select(func.count(Payment.id))) or 0) + 1
    )
    payment = Payment(
        reference=reference,
        booking_reference=booking.reference,
        amount_gnf=authoritative_amount,
        provider=provider_result.provider,
        phone=payload.phone.strip(),
        status=provider_result.status,
        receipt_number=build_receipt_number(reference),
        external_reference=provider_result.external_reference,
        checkout_url=(provider_result.checkout_url or "").strip() or None,
        paid_at=datetime.now(UTC).replace(tzinfo=None)
        if provider_result.status == "paid"
        else None,
    )
    db.add(payment)
    db.flush()
    synchronize_booking_from_payment(db, payment)

    append_audit(
        db,
        actor_id=current_user.id,
        action="payment.created",
        entity="payment",
        entity_id=reference,
        details={
            "booking_reference": booking.reference,
            "amount_gnf": authoritative_amount,
            "requested_amount_gnf": payload.amount_gnf,
            "provider": provider_result.provider,
            "status": provider_result.status,
            "receipt_number": payment.receipt_number,
            "external_reference": provider_result.external_reference,
            "checkout_url_persisted": bool(payment.checkout_url),
        },
    )
    db.commit()
    db.refresh(payment)
    _notify_payment_best_effort(db, booking, payment)

    return _payment_payload(payment, message=provider_result.message)


# Le remboursement historique marquait immédiatement `Payment.status=refunded`
# puis demandait d'effectuer le vrai remboursement Mobile Money manuellement.
# On retire cette route avant l'agrégation et on la remplace par le workflow
# requested -> approved/rejected -> completed avec preuve externe.
_legacy_refund_path = "/payments/{reference}/refund"
_legacy_refund_routes = [
    route
    for route in legacy_payments.router.routes
    if getattr(route, "path", None) == _legacy_refund_path
    and "POST" in (getattr(route, "methods", set()) or set())
]
if len(_legacy_refund_routes) != 1:
    raise RuntimeError(
        f"Expected exactly one legacy POST {_legacy_refund_path} route, found {len(_legacy_refund_routes)}"
    )
legacy_payments.router.routes[:] = [
    route for route in legacy_payments.router.routes if route not in _legacy_refund_routes
]
router.routes.extend(payment_refunds.router.routes)
