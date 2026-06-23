"""
Notifications schedulées — CodeRoute Guinée

Jobs disponibles (à appeler via cron ou endpoint admin) :
  1. exam_reminder_24h  — Rappel examen à J-24h (SMS + email)
  2. exam_reminder_2h   — Rappel examen à J-2h (SMS uniquement)
  3. payment_pending_7d — Alerte paiements en attente > 7 jours
  4. weekly_admin_digest — Résumé hebdo aux super-admins (lundi 8h)

Usage via script cron :
  python -m app.scheduled_notifications --job exam_reminder_24h

Usage via endpoint admin :
  POST /api/v1/admin/notifications/run-job?job=exam_reminder_24h
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models_booking import Booking
from app.models_candidate import Candidate
from app.models_session import ExamSession

log = logging.getLogger("coderoute.scheduler")


# ── Types ─────────────────────────────────────────────────────────────────────

@dataclass
class JobResult:
    job: str
    processed: int = 0
    sent: int = 0
    failed: int = 0
    errors: list[str] = field(default_factory=list)
    duration_ms: float = 0.0

    def to_dict(self) -> dict:
        return {
            "job":       self.job,
            "processed": self.processed,
            "sent":      self.sent,
            "failed":    self.failed,
            "errors":    self.errors[:10],   # limiter la taille
            "duration_ms": round(self.duration_ms),
        }


# ── Job 1 — Rappel examen J-24h ──────────────────────────────────────────────

def job_exam_reminder_24h(db: Session) -> JobResult:
    """
    Envoie un SMS + email à tous les candidats dont l'examen est
    dans 22h–26h (fenêtre de 4h pour absorber les décalages cron).
    """
    import time
    result = JobResult(job="exam_reminder_24h")
    start  = time.time()

    now    = datetime.now(UTC).replace(tzinfo=None)
    win_lo = now + timedelta(hours=22)
    win_hi = now + timedelta(hours=26)

    sessions = db.scalars(
        select(ExamSession).where(
            ExamSession.starts_at >= win_lo,
            ExamSession.starts_at <= win_hi,
            ExamSession.status.in_(["open", "planned"]),
        )
    ).all()

    for session in sessions:
        bookings = db.scalars(
            select(Booking).where(
                Booking.session_id == session.id,
                Booking.status == "confirmed",
            )
        ).all()

        for booking in bookings:
            result.processed += 1
            candidate = db.get(Candidate, booking.candidate_id)
            if not candidate:
                continue

            name        = f"{candidate.first_name} {candidate.last_name}"
            session_str = session.starts_at.strftime("%d/%m/%Y à %Hh%M")

            # SMS (canal principal en Guinée)
            if candidate.phone:
                try:
                    from app.orange_sms import send_exam_reminder_sms
                    send_exam_reminder_sms(
                        phone         = candidate.phone,
                        candidate_name = name,
                        hours_before  = 24,
                        session_date  = session_str,
                        center_name   = "votre centre",
                    )
                    result.sent += 1
                except Exception as e:
                    result.failed += 1
                    result.errors.append(f"SMS {candidate.phone}: {e}")

            # Email (canal secondaire)
            if candidate.email:
                try:
                    from app.email_service import send_convocation
                    send_convocation(
                        to_email          = candidate.email,
                        candidate_name    = name,
                        booking_reference = booking.reference,
                        session_date      = session_str,
                        center_name       = "Centre agréé DNTT",
                        center_address    = "Voir votre convocation",
                        qr_verification_url = f"https://coderoute.gov.gn/verify/{booking.reference}",
                    )
                    result.sent += 1
                except Exception as e:
                    result.failed += 1
                    result.errors.append(f"Email {candidate.email}: {e}")

    result.duration_ms = (time.time() - start) * 1000
    log.info("[%s] %d traités, %d envois, %d erreurs (%.0fms)",
             result.job, result.processed, result.sent, result.failed, result.duration_ms)
    return result


# ── Job 2 — Rappel examen J-2h ───────────────────────────────────────────────

def job_exam_reminder_2h(db: Session) -> JobResult:
    """SMS uniquement — examen dans 1h30–2h30."""
    import time
    result = JobResult(job="exam_reminder_2h")
    start  = time.time()

    now    = datetime.now(UTC).replace(tzinfo=None)
    win_lo = now + timedelta(minutes=90)
    win_hi = now + timedelta(minutes=150)

    sessions = db.scalars(
        select(ExamSession).where(
            ExamSession.starts_at >= win_lo,
            ExamSession.starts_at <= win_hi,
            ExamSession.status.in_(["open", "planned"]),
        )
    ).all()

    for session in sessions:
        bookings = db.scalars(
            select(Booking).where(
                Booking.session_id == session.id,
                Booking.status == "confirmed",
            )
        ).all()

        for booking in bookings:
            result.processed += 1
            candidate = db.get(Candidate, booking.candidate_id)
            if not candidate or not candidate.phone:
                continue

            try:
                from app.orange_sms import send_exam_reminder_sms
                send_exam_reminder_sms(
                    phone         = candidate.phone,
                    candidate_name = f"{candidate.first_name} {candidate.last_name}",
                    hours_before  = 2,
                    session_date  = session.starts_at.strftime("%d/%m/%Y à %Hh%M"),
                    center_name   = "votre centre",
                )
                result.sent += 1
            except Exception as e:
                result.failed += 1
                result.errors.append(f"SMS {candidate.phone}: {e}")

    result.duration_ms = (time.time() - start) * 1000
    log.info("[%s] %d traités, %d envois, %d erreurs",
             result.job, result.processed, result.sent, result.failed)
    return result


# ── Job 3 — Paiements en attente > 7 jours ────────────────────────────────────

def job_payment_pending_7d(db: Session) -> JobResult:
    """
    Alerte les candidats dont le paiement est en attente depuis > 7 jours.
    Limite : max 50 candidats par run pour ne pas saturer l'API SMS.
    """
    import time

    from app.models_payment import Payment
    result = JobResult(job="payment_pending_7d")
    start  = time.time()

    cutoff = datetime.now(UTC).replace(tzinfo=None) - timedelta(days=7)
    payments = db.scalars(
        select(Payment).where(
            Payment.status == "pending",
            Payment.created_at <= cutoff,
        ).limit(50)
    ).all()

    for payment in payments:
        result.processed += 1
        # Trouver le candidat via booking
        booking = db.scalar(
            select(Booking).where(Booking.reference == payment.booking_reference)
        )
        if not booking:
            continue

        candidate = db.get(Candidate, booking.candidate_id)
        if not candidate or not candidate.phone:
            continue

        try:
            from app.orange_sms import send_sms
            msg = (
                f"CodeRoute GN: {candidate.first_name}, "
                f"votre paiement {payment.reference} est toujours en attente. "
                f"Regularisez sur coderoute.gov.gn pour confirmer votre examen."
            )
            send_sms(candidate.phone, msg[:160])
            result.sent += 1
        except Exception as e:
            result.failed += 1
            result.errors.append(str(e))

    result.duration_ms = (time.time() - start) * 1000
    log.info("[%s] %d traités, %d envois", result.job, result.processed, result.sent)
    return result


# ── Dispatcher ────────────────────────────────────────────────────────────────

JOBS: dict[str, object] = {
    "exam_reminder_24h":  job_exam_reminder_24h,
    "exam_reminder_2h":   job_exam_reminder_2h,
    "payment_pending_7d": job_payment_pending_7d,
}


def run_job(job_name: str) -> JobResult:
    """Lance un job par son nom. Gère la session DB."""
    fn = JOBS.get(job_name)
    if fn is None:
        return JobResult(job=job_name, errors=[f"Job inconnu : {job_name}"])

    db = SessionLocal()
    try:
        return fn(db)  # type: ignore[call-arg]
    except Exception as e:
        log.error("[%s] Erreur inattendue : %s", job_name, e, exc_info=True)
        return JobResult(job=job_name, errors=[str(e)])
    finally:
        db.close()


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse
    import json

    parser = argparse.ArgumentParser(description="Notifications schedulées CodeRoute")
    parser.add_argument("--job", required=True, choices=list(JOBS),
                        help="Nom du job à exécuter")
    args = parser.parse_args()

    result = run_job(args.job)
    print(json.dumps(result.to_dict(), indent=2))
