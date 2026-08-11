from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.deps import get_current_user, require_roles
from app.models_audit import AuditLog
from app.models_booking import Booking
from app.models_payment import Payment
from app.models_payment_refund import PaymentRefundRequest
from app.models_user import User
from app.payment_rules import assert_payment_booking_access

router = APIRouter(prefix="/payments", tags=["payments"])

_OPEN_REFUND_STATUSES = {"requested", "approved"}
_FINAL_REFUND_STATUSES = {"rejected", "completed"}


class RefundCreateIn(BaseModel):
    reason: str = Field(min_length=10, max_length=1000)


class RefundDecisionIn(BaseModel):
    decision: Literal["approved", "rejected"]
    reason: str = Field(min_length=5, max_length=1000)


class RefundCompleteIn(BaseModel):
    provider_refund_reference: str = Field(min_length=5, max_length=200)
    evidence_reference: str = Field(min_length=5, max_length=255)
    notes: str = Field(min_length=5, max_length=2000)


class RefundRead(BaseModel):
    id: str
    payment_id: str
    booking_reference: str
    amount_gnf: int
    provider: str
    requested_by_id: str
    reason: str
    status: str
    decision_reason: str | None = None
    decided_by_id: str | None = None
    provider_refund_reference: str | None = None
    evidence_reference: str | None = None
    completion_notes: str | None = None
    requested_at: datetime
    decided_at: datetime | None = None
    completed_at: datetime | None = None

    model_config = {"from_attributes": True}


def _locked_refund(db: Session, refund_id: str) -> PaymentRefundRequest:
    item = db.scalar(
        select(PaymentRefundRequest)
        .where(PaymentRefundRequest.id == refund_id)
        .with_for_update()
    )
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Demande de remboursement introuvable")
    return item


def _booking_for_refund(db: Session, item: PaymentRefundRequest, *, lock: bool = False) -> Booking | None:
    query = select(Booking).where(Booking.reference == item.booking_reference)
    if lock:
        query = query.with_for_update()
    return db.scalar(query)


@router.post("/{reference}/refund", response_model=RefundRead, status_code=status.HTTP_202_ACCEPTED)
def request_refund(
    reference: str,
    payload: RefundCreateIn,
    response: Response,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PaymentRefundRequest:
    payment = db.scalar(
        select(Payment).where(Payment.reference == reference).with_for_update()
    )
    if payment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Paiement introuvable")

    booking = db.scalar(select(Booking).where(Booking.reference == payment.booking_reference))
    if booking is None:
        if current_user.role not in {"admin", "super_admin"}:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Accès paiement refusé.")
    else:
        assert_payment_booking_access(db, current_user, booking)

    payment_status = (payment.status or "").strip().lower()
    if payment_status == "refunded":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "PAYMENT_ALREADY_REFUNDED",
                "message": "Ce paiement est déjà enregistré comme remboursé.",
                "payment_reference": payment.reference,
            },
        )
    if payment_status != "paid":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "REFUND_PAYMENT_NOT_SETTLED",
                "message": "Une demande de remboursement ne peut être ouverte que pour un paiement confirmé comme payé.",
                "payment_status": payment_status,
            },
        )

    existing = db.scalar(
        select(PaymentRefundRequest)
        .where(PaymentRefundRequest.payment_id == payment.id)
        .order_by(PaymentRefundRequest.requested_at.desc())
        .limit(1)
    )
    if existing is not None:
        if existing.status in _OPEN_REFUND_STATUSES:
            response.status_code = status.HTTP_200_OK
            return existing
        if existing.status == "completed":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "code": "PAYMENT_ALREADY_REFUNDED",
                    "message": "Le remboursement de ce paiement a déjà été finalisé.",
                    "refund_id": existing.id,
                },
            )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "REFUND_REQUEST_ALREADY_DECIDED",
                "message": "Une demande de remboursement existe déjà pour ce paiement et a reçu une décision. Une nouvelle demande nécessite une réouverture administrative explicite.",
                "refund_id": existing.id,
                "refund_status": existing.status,
            },
        )

    item = PaymentRefundRequest(
        payment_id=payment.id,
        booking_reference=payment.booking_reference,
        amount_gnf=payment.amount_gnf,
        provider=payment.provider,
        requested_by_id=current_user.id,
        reason=payload.reason.strip(),
        status="requested",
    )
    db.add(item)
    db.flush()
    db.add(
        AuditLog(
            actor_id=current_user.id,
            action="payment.refund_requested",
            entity="payment_refund",
            entity_id=item.id,
            details={
                "payment_reference": payment.reference,
                "booking_reference": payment.booking_reference,
                "amount_gnf": payment.amount_gnf,
                "provider": payment.provider,
                "booking_status": booking.status if booking else None,
                "reason": item.reason,
            },
        )
    )
    db.commit()
    db.refresh(item)
    return item


@router.get("/refunds", response_model=list[RefundRead])
def list_refunds(
    refund_status: str | None = Query(default=None, alias="status"),
    limit: int = Query(default=100, ge=1, le=300),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "super_admin")),
) -> list[PaymentRefundRequest]:
    query = select(PaymentRefundRequest)
    if refund_status:
        query = query.where(PaymentRefundRequest.status == refund_status.strip().lower())
    return list(db.scalars(query.order_by(PaymentRefundRequest.requested_at.desc()).limit(limit)).all())


@router.get("/refunds/{refund_id}", response_model=RefundRead)
def get_refund(
    refund_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PaymentRefundRequest:
    item = db.get(PaymentRefundRequest, refund_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Demande de remboursement introuvable")
    if current_user.role not in {"admin", "super_admin"}:
        payment = db.get(Payment, item.payment_id)
        booking = _booking_for_refund(db, item)
        if payment is None or booking is None:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Accès remboursement refusé.")
        assert_payment_booking_access(db, current_user, booking)
    return item


@router.post("/refunds/{refund_id}/decision", response_model=RefundRead)
def decide_refund(
    refund_id: str,
    payload: RefundDecisionIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "super_admin")),
) -> PaymentRefundRequest:
    item = _locked_refund(db, refund_id)
    decision = payload.decision

    if item.status in _FINAL_REFUND_STATUSES:
        if item.status == decision:
            return item
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "REFUND_DECISION_ALREADY_FINAL",
                "message": "Cette demande de remboursement a déjà reçu une décision finale.",
                "refund_status": item.status,
            },
        )
    if item.status == "approved":
        if decision == "approved":
            return item
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "REFUND_ALREADY_APPROVED",
                "message": "Cette demande est déjà approuvée et attend une preuve de remboursement opérateur.",
            },
        )
    if item.status != "requested":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="État de remboursement non décidable")

    now = datetime.now(UTC).replace(tzinfo=None)
    item.status = decision
    item.decision_reason = payload.reason.strip()
    item.decided_by_id = current_user.id
    item.decided_at = now
    db.add(item)
    db.add(
        AuditLog(
            actor_id=current_user.id,
            action=f"payment.refund_{decision}",
            entity="payment_refund",
            entity_id=item.id,
            details={
                "payment_id": item.payment_id,
                "booking_reference": item.booking_reference,
                "amount_gnf": item.amount_gnf,
                "provider": item.provider,
                "decision_reason": item.decision_reason,
            },
        )
    )
    db.commit()
    db.refresh(item)
    return item


@router.post("/refunds/{refund_id}/complete", response_model=RefundRead)
def complete_refund(
    refund_id: str,
    payload: RefundCompleteIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "super_admin")),
) -> PaymentRefundRequest:
    item = _locked_refund(db, refund_id)
    provider_reference = payload.provider_refund_reference.strip()
    evidence_reference = payload.evidence_reference.strip()

    if item.status == "completed":
        if item.provider_refund_reference == provider_reference and item.evidence_reference == evidence_reference:
            return item
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "REFUND_COMPLETION_ALREADY_RECORDED",
                "message": "Le remboursement est déjà finalisé avec une autre référence de preuve.",
            },
        )
    if item.status != "approved":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "REFUND_APPROVAL_REQUIRED",
                "message": "Le remboursement doit être approuvé avant d'enregistrer sa réalisation opérateur.",
                "refund_status": item.status,
            },
        )

    payment = db.scalar(select(Payment).where(Payment.id == item.payment_id).with_for_update())
    if payment is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Paiement du remboursement introuvable")
    if payment.status != "paid":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "REFUND_PAYMENT_STATUS_CHANGED",
                "message": "Le statut du paiement a changé depuis la demande. Un rapprochement manuel est requis avant finalisation.",
                "payment_status": payment.status,
            },
        )

    booking = _booking_for_refund(db, item, lock=True)
    if booking is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Réservation du remboursement introuvable")

    now = datetime.now(UTC).replace(tzinfo=None)
    previous_booking_status = booking.status
    item.status = "completed"
    item.provider_refund_reference = provider_reference
    item.evidence_reference = evidence_reference
    item.completion_notes = payload.notes.strip()
    item.completed_at = now
    payment.status = "refunded"

    # Une place non consommée peut être libérée. Après check-in, on préserve le
    # statut historique du passage et on n'efface jamais l'événement physique.
    if booking.status in {"confirmed", "pending_payment", "paid"}:
        booking.status = "cancelled"
        booking.cancelled_at = now
    booking.notes = (
        (booking.notes or "")
        + f" | Remboursement enregistré {item.id} — preuve {evidence_reference}"
    ).strip(" |")

    db.add(item)
    db.add(payment)
    db.add(booking)
    db.add(
        AuditLog(
            actor_id=current_user.id,
            action="payment.refund_completed",
            entity="payment_refund",
            entity_id=item.id,
            details={
                "payment_reference": payment.reference,
                "booking_reference": booking.reference,
                "amount_gnf": payment.amount_gnf,
                "provider": payment.provider,
                "provider_refund_reference": provider_reference,
                "evidence_reference": evidence_reference,
                "booking_status_before": previous_booking_status,
                "booking_status_after": booking.status,
                "completion_mode": "operator_attested_external_evidence",
            },
        )
    )
    db.commit()
    db.refresh(item)
    return item
