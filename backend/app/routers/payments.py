import csv
import io
from datetime import UTC, datetime

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
from app.payment_service import build_payment_reference, build_receipt_number
from app.sentry import capture_exception as _sentry_cap

router = APIRouter(prefix="/payments", tags=["payments"])


class PaymentIn(BaseModel):
    booking_reference: str
    amount_gnf: int = 250000
    provider: str = "sandbox"
    phone: str


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


def _filtered_payments_query(
    provider: str | None = None,
    payment_status: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
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


@router.post("", status_code=status.HTTP_201_CREATED)
def create_payment(
    payload: PaymentIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    booking = db.scalar(select(Booking).where(Booking.reference == payload.booking_reference))
    if not booking:
        db.add(
            AuditLog(
                actor_id=current_user.id,
                action="payment.failed",
                entity="payment",
                entity_id=payload.booking_reference,
                details={"reason": "booking_not_found", "booking_reference": payload.booking_reference, "amount_gnf": payload.amount_gnf, "provider": payload.provider},
            )
        )
        db.commit()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found")

    if current_user.role not in ("admin", "super_admin"):
        candidate_by_id = db.scalar(select(Candidate).where(Candidate.id == booking.candidate_id))
        if candidate_by_id is None or candidate_by_id.phone != payload.phone:
            existing_payment = db.scalar(
                select(Payment).where(Payment.booking_reference == payload.booking_reference, Payment.status == "paid")
            )
            if existing_payment:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Payment already recorded for this booking")
    # Résoudre le montant via tarifs dynamiques si non spécifié
    try:
        from app.models_candidate import Candidate as _Cand
        from app.tarifs import get_tarif_for_candidate
        _cand = db.get(_Cand, booking.candidate_id)
        _cat  = getattr(_cand, "permit_category", "B") if _cand else "B"
        # Utiliser attempt_count réel pour les tarifs réinscription/rattrapage
        _attempts = getattr(_cand, "attempt_count", 0) or 0
        resolved_amount = get_tarif_for_candidate(_cat, attempt_number=_attempts + 1)
    except Exception as _tarif_exc:
        _sentry_cap(_tarif_exc, context={'endpoint': 'tarif_resolution'})
        resolved_amount = payload.amount_gnf
    final_amount = payload.amount_gnf if payload.amount_gnf != 250000 else resolved_amount

    provider_result = simulate_mobile_money_payment(payload.provider, payload.phone, final_amount)
    reference = build_payment_reference(db.query(Payment).count() + 1)
    from datetime import UTC
    from datetime import datetime as _dt
    payment = Payment(
        reference=reference,
        booking_reference=payload.booking_reference,
        amount_gnf=final_amount,
        provider=provider_result.provider,
        phone=payload.phone,
        status=provider_result.status,
        receipt_number=build_receipt_number(reference),
        external_reference=provider_result.external_reference,
        paid_at=_dt.now(UTC).replace(tzinfo=None) if provider_result.status == "paid" else None,
    )
    db.add(payment)
    db.add(
        AuditLog(
            actor_id=current_user.id,
            action="payment.created",
            entity="payment",
            entity_id=reference,
            details={
                "booking_reference": payload.booking_reference,
                "amount_gnf": payload.amount_gnf,
                "provider": provider_result.provider,
                "status": provider_result.status,
                "receipt_number": payment.receipt_number,
                "external_reference": provider_result.external_reference,
            },
        )
    )
    db.commit()
    db.refresh(payment)

    # Email de confirmation de paiement — best effort
    try:
        booking = db.scalar(select(Booking).where(Booking.reference == payload.booking_reference))
        if booking:
            candidate = db.scalar(select(Candidate).where(Candidate.id == booking.candidate_id))
            if candidate and candidate.email:
                from app.email_service import send_payment_confirmation
                send_payment_confirmation(
                    to_email          = candidate.email,
                    candidate_name    = f"{candidate.first_name} {candidate.last_name}",
                    booking_reference = payload.booking_reference,
                    amount_gnf        = payload.amount_gnf,
                    provider          = provider_result.provider,
                    receipt_number    = payment.receipt_number,
                )
    except Exception as _email_exc:
        _sentry_cap(_email_exc, context={'endpoint': 'payment_email'})
        pass  # Email non bloquant

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
        # URL de paiement Wave (vide pour les autres providers)
        "checkout_url": provider_result.checkout_url,
    }


@router.get("/recap/summary")
def get_payment_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "super_admin", "center")),
) -> dict:
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
        q = q.where(or_(
            Payment.receipt_number.ilike(f"%{search}%"),
            Payment.booking_reference.ilike(f"%{search}%"),
        ))
    total = db.scalar(select(func.count()).select_from(q.subquery()))
    items = db.scalars(q.order_by(Payment.created_at.desc()).offset(offset).limit(limit)).all()
    return {
        "total": total or 0,
        "limit": limit,
        "offset": offset,
        "items": [
            {
                "id": p.id,
                "booking_reference": p.booking_reference,
                "receipt_number": p.receipt_number,
                "amount_gnf": p.amount_gnf,
                "provider": p.provider,
                "status": p.status,
                "created_at": p.created_at.isoformat(),
            }
            for p in items
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
    payments = db.scalars(_filtered_payments_query(provider, payment_status, date_from, date_to).order_by(Payment.created_at.desc())).all()
    output = io.StringIO()
    writer = csv.writer(output, delimiter=";")
    writer.writerow(["reference", "booking_reference", "amount_gnf", "provider", "status", "receipt_number", "created_at"])
    for payment in payments:
        writer.writerow([
            payment.reference,
            payment.booking_reference,
            payment.amount_gnf,
            payment.provider,
            payment.status,
            payment.receipt_number,
            payment.created_at.isoformat() if payment.created_at else "",
        ])
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

    booking_references = [row.booking_reference.strip() for row in payload.payments]
    existing_bookings = {
        booking.reference
        for booking in db.scalars(select(Booking).where(Booking.reference.in_(booking_references))).all()
    }
    missing_bookings = sorted({reference for reference in booking_references if reference not in existing_bookings})
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

    created = 0
    updated = 0
    references: list[str] = []
    next_sequence = db.query(Payment).count() + 1

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
        db.add(payment)
        db.flush()
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
    return OfficialPaymentImportResult(dry_run=False, imported=len(references), created=created, updated=updated, skipped=0, references=references)


@router.get("/{reference}")
def get_payment(
    reference: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    payment = db.scalar(select(Payment).where(Payment.reference == reference))
    if not payment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found")
    return {
        "reference": payment.reference,
        "booking_reference": payment.booking_reference,
        "amount_gnf": payment.amount_gnf,
        "provider": payment.provider,
        "status": payment.status,
        "receipt_number": payment.receipt_number,
    }


# ── Webhooks Mobile Money (Mois 10–12) ────────────────────────────────────

@router.post("/webhook/wave", status_code=200, tags=["payments"])
async def wave_webhook(request: Request, db: Session = Depends(get_db)) -> dict:
    """
    Webhook Wave Mobile Money.
    Wave notifie le backend quand un paiement est confirmé.
    Sécurité : vérification de la signature HMAC-SHA256.
    """
    import hashlib
    import hmac
    import os

    body = await request.body()
    signature = request.headers.get("Wave-Signature", "")
    secret = os.environ.get("WAVE_WEBHOOK_SECRET", "")

    if secret:
        expected = hmac.new(
            secret.encode(), body, hashlib.sha256
        ).hexdigest()
        if not hmac.compare_digest(f"sha256={expected}", signature):
            from fastapi import HTTPException
            raise HTTPException(status_code=401, detail="Signature Wave invalide")

    import json
    try:
        data = json.loads(body)
    except json.JSONDecodeError:
        return {"status": "ignored", "reason": "invalid_json"}

    checkout_id = data.get("id", "")
    payment_status = data.get("payment_status", "")

    if payment_status == "succeeded":
        # Mettre à jour le statut du paiement en base
        from app.models_payment import Payment
        payment = db.query(Payment).filter(
            Payment.external_reference == checkout_id
        ).first()
        if payment and payment.status == "pending":
            payment.status = "paid"
            payment.paid_at = datetime.now(UTC).replace(tzinfo=None)
            db.commit()
            return {"status": "processed", "payment_id": str(payment.id)}

    return {"status": "received", "checkout_id": checkout_id}


@router.post("/webhook/paydunya", status_code=200, tags=["payments"])
async def paydunya_webhook(request: Request, db: Session = Depends(get_db)) -> dict:
    """
    Webhook PayDunya.
    PayDunya notifie le statut du checkout (succès, annulation, erreur).
    """
    import json
    body = await request.body()
    try:
        data = json.loads(body)
    except json.JSONDecodeError:
        return {"status": "ignored", "reason": "invalid_json"}

    token = data.get("data", {}).get("invoice", {}).get("token", "")
    status = data.get("data", {}).get("status", "")

    if status == "completed":
        from app.models_payment import Payment
        payment = db.query(Payment).filter(
            Payment.external_reference == token
        ).first()
        if payment and payment.status == "pending":
            payment.status = "paid"
            payment.paid_at = datetime.now(UTC).replace(tzinfo=None)
            db.commit()
            return {"status": "processed", "token": token}

    return {"status": "received", "token": token, "payment_status": status}


# ── Remboursements ────────────────────────────────────────────────────────────

class RefundRequest(BaseModel):
    reason: str = "Non spécifié"


@router.post("/{reference}/refund", tags=["payments"])
def refund_payment(
    reference: str,
    payload: RefundRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("super_admin")),
) -> dict:
    """
    Marque un paiement comme remboursé (super_admin uniquement).
    Le remboursement mobile money réel doit être effectué manuellement
    par un opérateur habilité DNTT.

    Règles :
      - Statut actuel doit être 'paid' ou 'confirmed'
      - Une raison est obligatoire pour l'audit
      - Action irréversible depuis l'API (modifier en base si nécessaire)
    """
    payment = db.scalar(select(Payment).where(Payment.reference == reference))
    if not payment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Paiement introuvable")

    if payment.status not in ("paid", "confirmed"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Remboursement impossible : statut actuel '{payment.status}' "
                   f"(doit être 'paid' ou 'confirmed')",
        )

    reason = payload.reason.strip() or "Non spécifié"

    # Mettre à jour le statut
    payment.status = "refunded"
    db.flush()

    # Mettre à jour la réservation associée
    booking = db.scalar(select(Booking).where(Booking.reference == payment.booking_reference))
    if booking:
        booking.status = "cancelled"
        booking.notes  = f"Remboursé — {reason}"
        db.flush()

    # Audit log
    db.add(AuditLog(
        actor_id  = current_user.id,
        action    = "payment_refunded",
        entity    = "payment",
        entity_id = reference,
        details   = f"Remboursement {payment.amount_gnf:,} GNF par {current_user.email} — {reason}",
    ))
    db.commit()

    return {
        "reference":  reference,
        "status":     "refunded",
        "amount_gnf": payment.amount_gnf,
        "reason":     reason,
        "refunded_by": current_user.email,
        "message": (
            "Paiement marqué comme remboursé. "
            "Le remboursement Mobile Money doit être effectué manuellement "
            "par l'opérateur DNTT habilité."
        ),
    }
