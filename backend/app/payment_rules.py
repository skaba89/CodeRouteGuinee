from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models_booking import Booking
from app.models_candidate import Candidate
from app.models_payment import Payment
from app.models_session import ExamSession
from app.models_user import User
from app.tarifs import get_tarif_for_candidate

# Les alias acceptés restent explicites. Aucun provider inconnu ne doit jamais
# être transformé silencieusement en paiement sandbox accepté.
_PROVIDER_ALIASES = {
    "orange": "orange_money",
    "orange_money": "orange_money",
    "mtn": "mtn_money",
    "mtn_money": "mtn_money",
    "wave": "wave",
    "wave_money": "wave",
    "paydunya": "paydunya",
    "pay_dunya": "paydunya",
    "celcom": "celcom_money",
    "celcom_money": "celcom_money",
    "sandbox": "sandbox",
}
_PRODUCTION_PROVIDERS = {"orange_money", "mtn_money", "wave", "paydunya"}
_SANDBOX_PROVIDERS = _PRODUCTION_PROVIDERS | {"celcom_money", "sandbox"}
_LEGACY_AMOUNT_SENTINEL_GNF = 250_000
_PAYMENT_REFERENCE_LOCK_ID = 2026081101


def normalize_payment_provider(provider: str) -> str:
    value = (provider or "").strip().lower().replace(" ", "_")
    normalized = _PROVIDER_ALIASES.get(value)
    if normalized is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": "PAYMENT_PROVIDER_UNSUPPORTED",
                "message": "Provider de paiement non supporté.",
                "provider": value,
            },
        )

    settings = get_settings()
    mode = (settings.mobile_money_mode or "sandbox").strip().lower()
    allowed = _PRODUCTION_PROVIDERS if mode == "production" else _SANDBOX_PROVIDERS
    if normalized not in allowed:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "PAYMENT_PROVIDER_NOT_ENABLED",
                "message": "Ce provider n'est pas activé dans le mode de paiement courant.",
                "provider": normalized,
                "mode": mode,
            },
        )
    return normalized


def acquire_payment_reference_lock(db: Session) -> None:
    """Sérialise la génération GN-PAY-* sur PostgreSQL.

    SQLite reste no-op pour les tests. Le verrou transactionnel évite que deux
    paiements de réservations différentes calculent le même `count + 1`.
    """
    bind = db.get_bind()
    if bind.dialect.name == "postgresql":
        db.execute(text("SELECT pg_advisory_xact_lock(:lock_id)"), {"lock_id": _PAYMENT_REFERENCE_LOCK_ID})


def booking_candidate(db: Session, booking: Booking) -> Candidate | None:
    return db.get(Candidate, booking.candidate_id)


def assert_payment_booking_access(db: Session, current_user: User, booking: Booking) -> None:
    """Empêche les paiements/lectures horizontales entre citoyens et centres."""
    if current_user.role in {"admin", "super_admin"}:
        return

    candidate = booking_candidate(db, booking)
    if current_user.role == "candidate":
        owns = candidate is not None and (
            candidate.user_id == current_user.id
            or bool(candidate.email and candidate.email == current_user.email)
        )
        if owns:
            return
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cette réservation ne vous appartient pas.")

    if current_user.role == "driving_school":
        if candidate is not None and candidate.registered_by == current_user.id:
            return
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Ce candidat n'appartient pas à votre auto-école.")

    if current_user.role == "center":
        session = db.get(ExamSession, booking.session_id)
        if session and current_user.center_id and session.center_id == current_user.center_id:
            return
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cette réservation appartient à un autre centre.")

    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Accès paiement refusé.")


def resolve_authoritative_amount(db: Session, booking: Booking) -> int:
    candidate = booking_candidate(db, booking)
    if candidate is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "PAYMENT_CANDIDATE_MISSING", "message": "Candidat de la réservation introuvable."},
        )
    try:
        attempt_number = (candidate.attempt_count or 0) + 1
        amount = int(get_tarif_for_candidate(candidate.permit_category or "B", attempt_number=attempt_number))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "PAYMENT_TARIFF_UNAVAILABLE",
                "message": "Le tarif institutionnel ne peut pas être résolu. Aucun débit n'a été lancé.",
            },
        ) from exc
    if amount <= 0:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Tarif institutionnel invalide")
    return amount


def assert_payment_amount(requested_amount: int | None, authoritative_amount: int) -> None:
    """Le prix serveur est la seule source de vérité.

    `250000` est conservé comme sentinelle de compatibilité pour les anciennes
    versions du frontend : cette valeur est ignorée et le tarif serveur est
    quand même débité. Toute autre valeur fournie doit correspondre exactement
    au tarif courant.
    """
    if requested_amount is None or int(requested_amount) == _LEGACY_AMOUNT_SENTINEL_GNF:
        return
    if int(requested_amount) != int(authoritative_amount):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": "PAYMENT_AMOUNT_MISMATCH",
                "message": "Le montant envoyé ne correspond plus au tarif applicable. Rechargez le tarif avant de payer.",
                "expected_amount_gnf": authoritative_amount,
            },
        )


def synchronize_booking_from_payment(db: Session, payment: Payment) -> Booking | None:
    """Répercute un paiement confirmé sur la réservation sans rouvrir un dossier annulé."""
    booking = db.scalar(
        select(Booking).where(Booking.reference == payment.booking_reference).with_for_update()
    )
    if booking is None:
        return None
    if payment.status != "paid":
        return booking
    if booking.status == "cancelled":
        return booking

    # `checked_in` est conservé si une confirmation provider arrive tardivement.
    if booking.status in {"confirmed", "pending_payment", "paid"}:
        booking.status = "paid"
    booking.payment_reference = payment.reference
    db.add(booking)
    return booking


def center_payment_query(center_id: str):
    """Query des paiements appartenant à un centre, utilisée pour les agrégats."""
    if not center_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Agent centre non affecté à un centre.")
    return (
        select(Payment)
        .join(Booking, Payment.booking_reference == Booking.reference)
        .join(ExamSession, Booking.session_id == ExamSession.id)
        .where(ExamSession.center_id == center_id)
    )
