import csv
import io
import json
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from pydantic import BaseModel, Field
from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.deps import get_current_user, require_roles
from app.mobile_money import simulate_mobile_money_payment
from app.models_audit import AuditLog
from app.models_booking import Booking
from app.models_candidate import Candidate
from app.models_payment import Payment
from app.models_user import User
from app.payment_recap import summarize_payments
from app.payment_rules import (
    acquire_payment_reference_lock,
    assert_payment_amount,
    assert_payment_booking_access,
    center_payment_query,
    normalize_payment_provider,
    resolve_authoritative_amount,
    synchronize_booking_from_payment,
)
from app.payment_service import build_payment_reference, build_receipt_number
from app.payment_webhook_security import (
    parse_paydunya_payload,
    verify_paydunya_hash,
    verify_wave_signature,
)
from app.sentry import capture_exception as _sentry_cap

router = APIRouter(prefix="/payments", tags=["payments"])


class PaymentIn(BaseModel):
    booking_reference: str = Field(min_length=3, max_length=80)
    # Compatibilité : les anciennes UI envoient 250000 comme sentinelle. Le
    # serveur ne fait jamais confiance à ce montant et recalcule le tarif.
    amount_gnf: int | None = Field(default=None, gt=0, le=5_000_000)
    provider: str = Field(default="sandbox", min_length=2, max_length=80)
    phone: str = Field(min_length=5, max_length=50)


class OfficialPaymentImportRow(BaseModel):
    booking_reference: str = Field(min_length=3, max_length=80)
    amount_gnf: int = Field(gt=0, le=5_000_000)
    provider: str = Field(min_length=2, max_length=80)
    phone: str = Field(min_length=5, max_length=50)
    status: str = Field(default="paid", min_length=3, max_length=50)
    receipt_number: str = Field(min_length=3, max_length=100)
    created_at: datetime | None = None


class OfficialPaymentImportRequest(BaseModel):
    source: str = Field(min_length=3, max_length=120)
    reason: str = Field(min_length=5, max_length=255)
    dry_run: bool = False
    payments: list[OfficialPaymentImportRow] = Field(min_length=1, max_length=1000)


class OfficialPaymentImportResult(BaseModel):
    dry_run: bool = False
    imported: int
    created: int
    updated: int
    skipped: int
    references: list[str]


class RefundRequest(BaseModel):
    reason: str = Field(default="Non spécifié", max_length=500)


def _filtered_payments_query(
    provider: str | None = None,
    payment_status: str | None = None,
    date_from: datetime | str | None = None,
    date_to: datetime | str | None = None,
) -> Select[tuple[Payment]]:
    query = select(Payment)
    if provider:
        query = query.where(Payment.provider == provider)
    if payment_status:
        query = query.where(Payment.status == payment_status)
    if date_from:
        query = query.where(Payment.created_at >= date_from)
    if date_to:
        query = query.where(Payment.created_at <= date_to)
    return query


def _payment_amount_matches(payment: Payment, raw_amount: object) -> bool:
    if raw_amount in (None, ""):
        return True
    try:
        return Decimal(str(raw_amount)) == Decimal(payment.amount_gnf)
    except (InvalidOperation, TypeError, ValueError):
        return False


def _audit_webhook(db: Session, action: str, payment: Payment, extra: dict | None = None) -> None:
    details = {
        "payment_reference": payment.reference,
        "booking_reference": payment.booking_reference,
        "provider": payment.provider,
        "status": payment.status,
        "external_reference": payment.external_reference,
    }
    if extra:
        details.update(extra)
    db.add(
        AuditLog(
            actor_id=None,
            action=action,
            entity="payment",
            entity_id=payment.reference,
            details=details,
        )
    )


@router.post("", status_code=status.HTTP_201_CREATED)
def create_payment(
    payload: PaymentIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    # Verrouille la réservation avant le contrôle d'idempotence afin que deux
    # doubles-clics concurrents ne puissent pas lancer deux débits provider.
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
    if booking.status == "cancelled":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Cette réservation est annulée.")

    existing_open_payment = db.scalar(
        select(Payment).where(
            Payment.booking_reference == booking.reference,
            Payment.status.in_(["paid", "pending"]),
        )
    )
    if existing_open_payment:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "PAYMENT_ALREADY_EXISTS",
                "message": "Un paiement payé ou en attente existe déjà pour cette réservation.",
                "payment_reference": existing_open_payment.reference,
                "payment_status": existing_open_payment.status,
            },
        )

    authoritative_amount = resolve_authoritative_amount(db, booking)
    assert_payment_amount(payload.amount_gnf, authoritative_amount)
    provider = normalize_payment_provider(payload.provider)

    provider_result = simulate_mobile_money_payment(provider, payload.phone, authoritative_amount)

    acquire_payment_reference_lock(db)
    reference = build_payment_reference((db.scalar(select(func.count(Payment.id))) or 0) + 1)
    payment = Payment(
        reference=reference,
        booking_reference=booking.reference,
        amount_gnf=authoritative_amount,
        provider=provider_result.provider,
        phone=payload.phone.strip(),
        status=provider_result.status,
        receipt_number=build_receipt_number(reference),
        external_reference=provider_result.external_reference,
        paid_at=datetime.now(UTC).replace(tzinfo=None) if provider_result.status == "paid" else None,
    )
    db.add(payment)
    db.flush()
    synchronize_booking_from_payment(db, payment)

    from app.audit_chain import append_audit

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
        },
    )
    db.commit()
    db.refresh(payment)

    # Notifications non bloquantes : le reçu doit afficher le montant réellement
    # décidé par le serveur, jamais la valeur envoyée par le navigateur.
    try:
        candidate = db.get(Candidate, booking.candidate_id)
        if candidate and candidate.email:
            from app.email_service import send_payment_confirmation

            send_payment_confirmation(
                to_email=candidate.email,
                candidate_name=f"{candidate.first_name} {candidate.last_name}",
                booking_reference=booking.reference,
                amount_gnf=payment.amount_gnf,
                provider=provider_result.provider,
                receipt_number=payment.receipt_number,
            )
    except Exception as _email_exc:
        _sentry_cap(_email_exc, context={"endpoint": "payment_email"})

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
        "message": provider_result.message,
        "checkout_url": provider_result.checkout_url,
    }


@router.get("/recap/summary")
def get_payment_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "super_admin", "center")),
) -> dict:
    if current_user.role == "center":
        payments = db.scalars(center_payment_query(current_user.center_id or "")).all()
    else:
        payments = db.scalars(select(Payment)).all()
    return summarize_payments(payments)


@router.get("/admin/summary")
def get_admin_payment_summary(
    provider: str | None = None,
    payment_status: str | None = Query(default=None, alias="status"),
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "super_admin")),
) -> dict:
    payments = db.scalars(_filtered_payments_query(provider, payment_status, date_from, date_to)).all()
    summary = summarize_payments(payments)
    db.add(
        AuditLog(
            actor_id=current_user.id,
            action="payments.summary_viewed",
            entity="payment",
            entity_id="national-payments",
            details={
                "total_count": summary["total_count"],
                "total_amount_gnf": summary["total_amount_gnf"],
                "provider": provider,
                "status": payment_status,
                "date_from": date_from.isoformat() if date_from else None,
                "date_to": date_to.isoformat() if date_to else None,
            },
        )
    )
    db.commit()
    return summary


@router.get("/admin/list")
def get_admin_payment_list(
    provider: str | None = Query(default=None),
    payment_status: str | None = Query(default=None, alias="status"),
    date_from: str | None = Query(default=None),
    date_to: str | None = Query(default=None),
    search: str | None = Query(default=None, description="Recherche sur référence ou numéro reçu"),
    limit: int = Query(default=20, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "super_admin")),
) -> dict:
    q = _filtered_payments_query(provider, payment_status, date_from, date_to)
    if search:
        from sqlalchemy import or_

        q = q.where(
            or_(
                Payment.receipt_number.ilike(f"%{search}%"),
                Payment.booking_reference.ilike(f"%{search}%"),
            )
        )
    total = db.scalar(select(func.count()).select_from(q.subquery()))
    items = db.scalars(q.order_by(Payment.created_at.desc()).offset(offset).limit(limit)).all()
    return {
        "total": total or 0,
        "limit": limit,
        "offset": offset,
        "items": [
            {
                "id": item.id,
                "booking_reference": item.booking_reference,
                "receipt_number": item.receipt_number,
                "amount_gnf": item.amount_gnf,
                "provider": item.provider,
                "status": item.status,
                "created_at": item.created_at.isoformat(),
            }
            for item in items
        ],
    }


@router.get("/admin/export.csv")
def export_admin_payments_csv(
    provider: str | None = None,
    payment_status: str | None = Query(default=None, alias="status"),
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "super_admin")),
) -> Response:
    payments = db.scalars(
        _filtered_payments_query(provider, payment_status, date_from, date_to).order_by(Payment.created_at.desc())
    ).all()
    output = io.StringIO()
    writer = csv.writer(output, delimiter=";")
    writer.writerow(["reference", "booking_reference", "amount_gnf", "provider", "status", "receipt_number", "created_at"])
    for payment in payments:
        writer.writerow(
            [
                payment.reference,
                payment.booking_reference,
                payment.amount_gnf,
                payment.provider,
                payment.status,
                payment.receipt_number,
                payment.created_at.isoformat() if payment.created_at else "",
            ]
        )
    db.add(
        AuditLog(
            actor_id=current_user.id,
            action="payments.export_csv",
            entity="payment",
            entity_id="national-payments",
            details={
                "format": "csv",
                "payments_exported": len(payments),
                "total_amount_gnf": sum(payment.amount_gnf for payment in payments),
                "provider": provider,
                "status": payment_status,
                "date_from": date_from.isoformat() if date_from else None,
                "date_to": date_to.isoformat() if date_to else None,
            },
        )
    )
    db.commit()
    headers = {"Content-Disposition": "attachment; filename=coderoute-payments.csv"}
    return Response(content=output.getvalue(), media_type="text/csv", headers=headers)


@router.post("/admin/import-official", response_model=OfficialPaymentImportResult)
def import_official_payments(
    payload: OfficialPaymentImportRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "super_admin")),
) -> OfficialPaymentImportResult:
    normalized_receipts = [row.receipt_number.strip().upper() for row in payload.payments]
    duplicate_receipts = sorted({receipt for receipt in normalized_receipts if normalized_receipts.count(receipt) > 1})
    if duplicate_receipts:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"message": "Duplicate payment receipts in import payload", "receipt_numbers": duplicate_receipts},
        )

    normalized_statuses = {row.status.strip().lower() for row in payload.payments}
    unsupported_statuses = sorted(normalized_statuses - {"paid", "pending", "failed", "refunded", "confirmed"})
    if unsupported_statuses:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"message": "Unsupported payment status", "statuses": unsupported_statuses},
        )

    booking_references = [row.booking_reference.strip() for row in payload.payments]
    bookings = {
        booking.reference: booking
        for booking in db.scalars(select(Booking).where(Booking.reference.in_(booking_references))).all()
    }
    missing_bookings = sorted({reference for reference in booking_references if reference not in bookings})
    if missing_bookings:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"message": "Unknown booking references in import payload", "booking_references": missing_bookings},
        )

    existing_payments = {
        payment.receipt_number.upper(): payment
        for payment in db.scalars(select(Payment).where(Payment.receipt_number.in_(normalized_receipts))).all()
    }
    if payload.dry_run:
        existing_receipts = [receipt for receipt in normalized_receipts if receipt in existing_payments]
        return OfficialPaymentImportResult(
            dry_run=True,
            imported=len(normalized_receipts),
            created=len(normalized_receipts) - len(existing_receipts),
            updated=len(existing_receipts),
            skipped=0,
            references=[existing_payments[receipt].reference for receipt in existing_receipts],
        )

    acquire_payment_reference_lock(db)
    created = 0
    updated = 0
    references: list[str] = []
    next_sequence = (db.scalar(select(func.count(Payment.id))) or 0) + 1

    for row in payload.payments:
        receipt_number = row.receipt_number.strip().upper()
        payment = existing_payments.get(receipt_number)
        if payment is None:
            payment = Payment(reference=build_payment_reference(next_sequence), receipt_number=receipt_number)
            next_sequence += 1
            created += 1
        else:
            updated += 1
        payment.booking_reference = row.booking_reference.strip()
        payment.amount_gnf = row.amount_gnf
        payment.provider = row.provider.strip().lower()
        payment.phone = row.phone.strip()
        payment.status = row.status.strip().lower()
        payment.receipt_number = receipt_number
        if row.created_at:
            payment.created_at = row.created_at
        if payment.status == "paid" and payment.paid_at is None:
            payment.paid_at = row.created_at or datetime.now(UTC).replace(tzinfo=None)
        db.add(payment)
        db.flush()
        synchronize_booking_from_payment(db, payment)
        references.append(payment.reference)

    db.add(
        AuditLog(
            actor_id=current_user.id,
            action="payments.official_import",
            entity="payment",
            entity_id="official-import",
            details={
                "source": payload.source,
                "reason": payload.reason,
                "imported": len(references),
                "created": created,
                "updated": updated,
                "references": references[:50],
            },
        )
    )
    db.commit()
    return OfficialPaymentImportResult(
        dry_run=False,
        imported=len(references),
        created=created,
        updated=updated,
        skipped=0,
        references=references,
    )


@router.get("/{reference}")
def get_payment(
    reference: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    payment = db.scalar(select(Payment).where(Payment.reference == reference))
    if not payment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found")
    booking = db.scalar(select(Booking).where(Booking.reference == payment.booking_reference))
    if booking is None:
        if current_user.role not in {"admin", "super_admin"}:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Accès paiement refusé.")
    else:
        assert_payment_booking_access(db, current_user, booking)
    return {
        "reference": payment.reference,
        "booking_reference": payment.booking_reference,
        "amount_gnf": payment.amount_gnf,
        "provider": payment.provider,
        "status": payment.status,
        "receipt_number": payment.receipt_number,
    }


# ── Webhooks Mobile Money ────────────────────────────────────────────────────

@router.post("/webhook/wave", status_code=200, tags=["payments"])
async def wave_webhook(request: Request, db: Session = Depends(get_db)) -> dict:
    body = await request.body()
    verify_wave_signature(body, request.headers.get("Wave-Signature", ""))

    try:
        payload = json.loads(body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Payload Wave invalide")
    if not isinstance(payload, dict):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Payload Wave invalide")

    event_data = payload.get("data") if isinstance(payload.get("data"), dict) else payload
    checkout_id = str(event_data.get("id") or payload.get("id") or "")
    payment_status = str(event_data.get("payment_status") or payload.get("payment_status") or "").lower()

    if payment_status == "succeeded" and checkout_id:
        payment = db.scalar(select(Payment).where(Payment.external_reference == checkout_id).with_for_update())
        if payment:
            if payment.provider != "wave":
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Provider du paiement incohérent")
            if not _payment_amount_matches(payment, event_data.get("amount")):
                _audit_webhook(db, "payment.webhook_amount_mismatch", payment, {"source": "wave"})
                db.commit()
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Montant Wave incohérent")
            if payment.status == "pending":
                payment.status = "paid"
                payment.paid_at = datetime.now(UTC).replace(tzinfo=None)
                db.add(payment)
                synchronize_booking_from_payment(db, payment)
                _audit_webhook(db, "payment.webhook.wave", payment)
                db.commit()
            return {"status": "processed", "payment_id": str(payment.id), "payment_status": payment.status}

    return {"status": "received", "checkout_id": checkout_id, "payment_status": payment_status}


@router.post("/webhook/paydunya", status_code=200, tags=["payments"])
async def paydunya_webhook(request: Request, db: Session = Depends(get_db)) -> dict:
    body = await request.body()
    payload = parse_paydunya_payload(body, request.headers.get("content-type", ""))
    if not payload:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Payload PayDunya invalide")
    verify_paydunya_hash(payload)

    data = payload.get("data") if isinstance(payload.get("data"), dict) else {}
    invoice = data.get("invoice") if isinstance(data.get("invoice"), dict) else {}
    token = str(invoice.get("token") or data.get("token") or "")
    payment_status = str(data.get("status") or "").lower()

    if payment_status == "completed" and token:
        payment = db.scalar(select(Payment).where(Payment.external_reference == token).with_for_update())
        if payment:
            if payment.provider != "paydunya":
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Provider du paiement incohérent")
            if not _payment_amount_matches(payment, invoice.get("total_amount")):
                _audit_webhook(db, "payment.webhook_amount_mismatch", payment, {"source": "paydunya"})
                db.commit()
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Montant PayDunya incohérent")
            if payment.status == "pending":
                payment.status = "paid"
                payment.paid_at = datetime.now(UTC).replace(tzinfo=None)
                db.add(payment)
                synchronize_booking_from_payment(db, payment)
                _audit_webhook(db, "payment.webhook.paydunya", payment)
                db.commit()
            return {"status": "processed", "token": token, "payment_status": payment.status}

    return {"status": "received", "token": token, "payment_status": payment_status}


# ── Remboursements ────────────────────────────────────────────────────────────

@router.post("/{reference}/refund", tags=["payments"])
def refund_payment(
    reference: str,
    payload: RefundRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("super_admin")),
) -> dict:
    payment = db.scalar(select(Payment).where(Payment.reference == reference).with_for_update())
    if not payment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Paiement introuvable")

    if payment.status not in ("paid", "confirmed"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Remboursement impossible : statut actuel '{payment.status}' "
                "(doit être 'paid' ou 'confirmed')"
            ),
        )

    reason = payload.reason.strip() or "Non spécifié"
    now = datetime.now(UTC).replace(tzinfo=None)
    payment.status = "refunded"
    db.add(payment)

    booking = db.scalar(select(Booking).where(Booking.reference == payment.booking_reference).with_for_update())
    if booking:
        booking.status = "cancelled"
        booking.cancelled_at = now
        booking.notes = f"Remboursé — {reason}"
        db.add(booking)

    db.add(
        AuditLog(
            actor_id=current_user.id,
            action="payment_refunded",
            entity="payment",
            entity_id=reference,
            details={
                "amount_gnf": payment.amount_gnf,
                "booking_reference": payment.booking_reference,
                "reason": reason,
                "refunded_by": current_user.email,
                "refunded_at": now.isoformat(),
                "provider_refund": "manual_required",
            },
        )
    )
    db.commit()

    return {
        "reference": reference,
        "status": "refunded",
        "amount_gnf": payment.amount_gnf,
        "reason": reason,
        "refunded_by": current_user.email,
        "message": (
            "Paiement marqué comme remboursé. Le remboursement Mobile Money doit être effectué "
            "manuellement par l'opérateur DNTT habilité."
        ),
    }
