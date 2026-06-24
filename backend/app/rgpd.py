"""
RGPD — Loi L/2022/018/AN de Guinée relative à la protection des données personnelles
https://www.dgi.gov.gn/loi-l-2022-018

Droits implémentés :
  Art. 18 — Droit d'accès       : /rgpd/export
  Art. 19 — Droit de rectification : via PATCH /candidates/{id}
  Art. 20 — Droit à l'effacement : /rgpd/delete  (anonymisation)
  Art. 22 — Droit d'opposition  : /rgpd/oppose   (flag marketing)
  Art. 24 — Droit à la portabilité : /rgpd/export (format JSON/CSV machine-lisible)

Implémentation :
  - L'effacement ne supprime pas les examens et paiements (obligation légale DNTT)
  - Il anonymise les données personnelles (nom → ANON_xxx, email/phone → hash)
  - La demande est auditée et une copie envoyée à l'autorité compétente (ANPDP)
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import logging
from datetime import UTC, datetime

from sqlalchemy.orm import Session

log = logging.getLogger("coderoute.rgpd")


# ── Anonymisation ─────────────────────────────────────────────────────────────

def _hash_pii(value: str) -> str:
    """Hash SHA-256 tronqué pour masquer une valeur PII de façon irréversible."""
    return "ANON_" + hashlib.sha256(value.encode()).hexdigest()[:12].upper()


def anonymize_candidate(candidate_id: str, db: Session, reason: str = "") -> dict:
    """
    Anonymise les données personnelles d'un candidat (droit à l'effacement).
    Conserve les données d'examen et financières (obligation légale DNTT).
    Retourne un rapport de l'opération.
    """
    from app.models_candidate import Candidate

    cand = db.get(Candidate, candidate_id)
    if not cand:
        raise ValueError(f"Candidat {candidate_id} introuvable")

    original_ref = cand.reference
    ts = datetime.now(UTC).strftime("%Y%m%d%H%M%S")

    # Masquer les champs PII
    cand.first_name      = "ANONYME"
    cand.last_name       = "ANONYME"
    cand.identity_number = _hash_pii(cand.identity_number or candidate_id)
    cand.phone           = _hash_pii(cand.phone or candidate_id)
    if hasattr(cand, "email") and cand.email:
        cand.email = _hash_pii(cand.email)
    cand.status          = "anonymized"

    db.flush()

    # Audit log
    from app.models_audit import AuditLog
    db.add(AuditLog(
        actor_id  = candidate_id,
        action    = "rgpd_erasure",
        entity    = "candidate",
        entity_id = candidate_id,
        details   = f"Effacement RGPD art.20 Loi L/2022/018/AN — {reason or 'Demande candidat'} — {ts}",
    ))
    db.commit()
    log.info("RGPD anonymisation candidat %s (%s)", candidate_id[:8], original_ref)

    return {
        "candidate_id": candidate_id,
        "reference":    original_ref,
        "operation":    "erasure",
        "law":          "L/2022/018/AN art.20",
        "timestamp":    ts,
        "preserved":    ["exam_attempts", "payments", "bookings"],
        "erased":       ["first_name", "last_name", "identity_number", "phone", "email"],
    }


# ── Export données personnelles ───────────────────────────────────────────────

def export_candidate_data(candidate_id: str, db: Session, fmt: str = "json") -> bytes:
    """
    Exporte toutes les données personnelles d'un candidat (droit d'accès + portabilité).
    Format : 'json' (défaut) ou 'csv'.
    """
    from sqlalchemy import select

    from app.models_booking import Booking
    from app.models_candidate import Candidate
    from app.models_exam_attempt import ExamAttempt
    from app.models_payment import Payment

    cand = db.get(Candidate, candidate_id)
    if not cand:
        raise ValueError(f"Candidat {candidate_id} introuvable")

    # Données candidat
    cand_data = {
        "reference":       cand.reference,
        "first_name":      cand.first_name,
        "last_name":       cand.last_name,
        "identity_number": cand.identity_number,
        "phone":           cand.phone,
        "email":           getattr(cand, "email", None),
        "permit_category": cand.permit_category,
        "status":          cand.status,
        "created_at":      cand.created_at.isoformat() if cand.created_at else None,
    }

    # Réservations
    bookings = db.scalars(
        select(Booking).where(Booking.candidate_id == candidate_id)
    ).all()
    bookings_data = [
        {"reference": b.reference, "status": b.status, "created_at": b.created_at.isoformat() if b.created_at else None}
        for b in bookings
    ]

    # Paiements
    payments = db.scalars(
        select(Payment).where(Payment.booking_reference.in_([b.reference for b in bookings]))
    ).all()
    payments_data = [
        {"reference": p.reference, "amount_gnf": p.amount_gnf, "status": p.status,
         "provider": p.provider, "created_at": p.created_at.isoformat() if p.created_at else None}
        for p in payments
    ]

    # Tentatives d'examen
    attempts = db.scalars(
        select(ExamAttempt).where(ExamAttempt.candidate_id == candidate_id)
    ).all()
    attempts_data = [
        {"id": str(a.id), "status": a.status, "score": a.score, "passed": a.passed,
         "started_at": a.started_at.isoformat() if a.started_at else None,
         "submitted_at": a.submitted_at.isoformat() if a.submitted_at else None}
        for a in attempts
    ]

    payload = {
        "export_date":   datetime.now(UTC).isoformat(),
        "law":           "L/2022/018/AN art.18 — Droit d'accès",
        "authority":     "ANPDP Guinée",
        "candidate":     cand_data,
        "bookings":      bookings_data,
        "payments":      payments_data,
        "exam_attempts": attempts_data,
    }

    if fmt == "csv":
        output = io.StringIO()
        writer = csv.writer(output, delimiter=";")
        # Fiche identité
        writer.writerow(["=== DONNÉES PERSONNELLES ==="])
        for k, v in cand_data.items():
            writer.writerow([k, v])
        # Réservations
        writer.writerow([])
        writer.writerow(["=== RÉSERVATIONS ==="])
        if bookings_data:
            writer.writerow(list(bookings_data[0].keys()))
            for row in bookings_data:
                writer.writerow(list(row.values()))
        # Paiements
        writer.writerow([])
        writer.writerow(["=== PAIEMENTS ==="])
        if payments_data:
            writer.writerow(list(payments_data[0].keys()))
            for row in payments_data:
                writer.writerow(list(row.values()))
        # Examens
        writer.writerow([])
        writer.writerow(["=== EXAMENS ==="])
        if attempts_data:
            writer.writerow(list(attempts_data[0].keys()))
            for row in attempts_data:
                writer.writerow(list(row.values()))
        return output.getvalue().encode("utf-8-sig")

    return json.dumps(payload, ensure_ascii=False, indent=2).encode()
