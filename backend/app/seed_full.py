"""
Seed complet CodeRoute Guinée — Tous les profils de test réels.

Crée une base de données complète et opérationnelle avec :
  - 5 utilisateurs (super_admin, admin, 2 chefs de centre, 1 opérateur centre)
  - 3 centres agréés (Conakry, Kindia, Kankan)
  - 40 questions officielles catégorie B (banque réelle)
  - 3 sessions d'examen planifiées
  - 8 candidats avec parcours complets (paiement, réservation, examen)
  - Scénarios : admis, ajourné, en attente, fraude détectée

Usage :
    python -m app.seed_full

Comptes de test générés :
    super_admin@coderoute.gov.gn  / CodeRoute2026!
    admin.national@coderoute.gov.gn / CodeRoute2026!
    chef.conakry@coderoute.gov.gn / CodeRoute2026!
    chef.kindia@coderoute.gov.gn / CodeRoute2026!
    operateur.conakry@coderoute.gov.gn / CodeRoute2026!
"""
from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from sqlalchemy import select

from app.db.session import SessionLocal, init_db
from app.models_audit import AuditLog
from app.models_booking import Booking
from app.models_candidate import Candidate
from app.models_center import Center
from app.models_device_session import DeviceSession
from app.models_exam_attempt import ExamAttempt
from app.models_exam_question_trace import ExamQuestionTrace
from app.models_payment import Payment
from app.models_question import Question
from app.models_session import ExamSession
from app.models_user import User
from app.question_bank_gn import QUESTIONS_GN
from app.security import get_password_hash

SEED_PASSWORD = "CodeRoute2026!"
ALLOW_ENV = "ALLOW_DEMO_SEED_NON_DEV"


def _guard() -> None:
    from app.core.config import get_settings
    env = get_settings().environment.lower()
    if env == "development":
        return
    if os.getenv(ALLOW_ENV) == "true":
        print(f"⚠️  Seed autorisé explicitement sur {env}")
        return
    raise RuntimeError(
        f"Seed bloqué en {env}. Définir {ALLOW_ENV}=true sur une base jetable."
    )


# ── UTILISATEURS ──────────────────────────────────────────────────────────

USERS = [
    {
        "email": "super_admin@coderoute.gov.gn",
        "full_name": "Directeur National CodeRoute",
        "role": "super_admin",
        "description": "Super administrateur — accès total",
    },
    {
        "email": "admin.national@coderoute.gov.gn",
        "full_name": "Responsable Examens National",
        "role": "admin",
        "description": "Administrateur national — gestion examens",
    },
    {
        "email": "chef.conakry@coderoute.gov.gn",
        "full_name": "Chef Centre Kaloum Conakry",
        "role": "center",
        "description": "Chef de centre — Centre Conakry Kaloum",
    },
    {
        "email": "chef.kindia@coderoute.gov.gn",
        "full_name": "Chef Centre Kindia",
        "role": "center",
        "description": "Chef de centre — Centre Kindia",
    },
    {
        "email": "operateur.conakry@coderoute.gov.gn",
        "full_name": "Opérateur Centre Kaloum",
        "role": "center",
        "description": "Opérateur de saisie — Centre Conakry Kaloum",
    },
]


def seed_users(db) -> dict[str, User]:
    users = {}
    for u in USERS:
        existing = db.scalar(select(User).where(User.email == u["email"]))
        if existing:
            users[u["email"]] = existing
            continue
        user = User(
            email=u["email"],
            full_name=u["full_name"],
            password_hash=get_password_hash(SEED_PASSWORD),
            role=u["role"],
            is_active=True,
        )
        db.add(user)
        db.flush()
        users[u["email"]] = user
    db.commit()
    print(f"  ✅ {len(users)} utilisateurs")
    return users


# ── CENTRES ───────────────────────────────────────────────────────────────

CENTERS = [
    {
        "code": "CRG-CONAKRY-KALOUM-001",
        "name": "Centre d'Examen Code de la Route — Kaloum",
        "city": "Conakry",
        "address": "Boulevard du Commerce, Kaloum, Conakry",
        "capacity": 30,
        "status": "accredited",
    },
    {
        "code": "CRG-KINDIA-001",
        "name": "Centre d'Examen Code de la Route — Kindia",
        "city": "Kindia",
        "address": "Route Nationale 1, Kindia",
        "capacity": 20,
        "status": "accredited",
    },
    {
        "code": "CRG-KANKAN-001",
        "name": "Centre d'Examen Code de la Route — Kankan",
        "city": "Kankan",
        "address": "Avenue Félix Houphouët-Boigny, Kankan",
        "capacity": 15,
        "status": "accredited",
    },
]


def seed_centers(db) -> dict[str, Center]:
    centers = {}
    for c in CENTERS:
        existing = db.scalar(select(Center).where(Center.code == c["code"]))
        if existing:
            centers[c["code"]] = existing
            continue
        center = Center(**c)
        db.add(center)
        db.flush()
        centers[c["code"]] = center
    db.commit()
    print(f"  ✅ {len(centers)} centres")
    return centers


# ── QUESTIONS ─────────────────────────────────────────────────────────────

def seed_questions(db) -> list[Question]:
    existing = db.scalars(select(Question).where(Question.is_active.is_(True))).all()
    if len(existing) >= 40:
        print(f"  ✅ {len(existing)} questions (déjà présentes)")
        return list(existing)

    questions = []
    for q in QUESTIONS_GN:
        obj = Question(
            category=q["category"],
            text=q["text"],
            options=q["options"],
            correct_answer=q["correct_answer"],
            explanation=q.get("explanation", ""),
            is_active=True,
        )
        db.add(obj)
        questions.append(obj)
    db.commit()
    # Rafraîchir pour récupérer les IDs
    for q in questions:
        db.refresh(q)
    print(f"  ✅ {len(questions)} questions créées")
    return questions


# ── SESSIONS ──────────────────────────────────────────────────────────────

def seed_sessions(db, centers: dict[str, Center]) -> list[ExamSession]:
    now = datetime.now(UTC).replace(tzinfo=None)
    session_defs = [
        {
            "reference": "GN-SESSION-2026-CONAKRY-001",
            "center_code": "CRG-CONAKRY-KALOUM-001",
            "starts_at": now + timedelta(days=7),
            "capacity": 30,
        },
        {
            "reference": "GN-SESSION-2026-CONAKRY-002",
            "center_code": "CRG-CONAKRY-KALOUM-001",
            "starts_at": now + timedelta(days=14),
            "capacity": 30,
        },
        {
            "reference": "GN-SESSION-2026-KINDIA-001",
            "center_code": "CRG-KINDIA-001",
            "starts_at": now + timedelta(days=10),
            "capacity": 20,
        },
    ]
    sessions = []
    for s in session_defs:
        existing = db.scalar(select(ExamSession).where(ExamSession.reference == s["reference"]))
        if existing:
            sessions.append(existing)
            continue
        center = centers[s["center_code"]]
        session = ExamSession(
            reference=s["reference"],
            center_id=center.id,
            starts_at=s["starts_at"],
            capacity=s["capacity"],
        )
        db.add(session)
        db.flush()
        sessions.append(session)
    db.commit()
    print(f"  ✅ {len(sessions)} sessions planifiées")
    return sessions


# ── CANDIDATS ET PARCOURS COMPLETS ────────────────────────────────────────

CANDIDATES_DATA = [
    # Admis — parcours complet (réservation + paiement + examen réussi)
    {
        "reference": "GN-CAND-2026-001",
        "first_name": "Mamadou",
        "last_name": "Diallo",
        "identity_number": "NINA-GN-2001-001234",
        "phone": "+224620111001",
        "permit_category": "B",
        "scenario": "passed",
        "session_index": 0,
        "correct_ratio": 38,  # 38/40 → admis
    },
    # Ajourné — examen passé, non admis
    {
        "reference": "GN-CAND-2026-002",
        "first_name": "Fatoumata",
        "last_name": "Camara",
        "identity_number": "NINA-GN-2002-005678",
        "phone": "+224620111002",
        "permit_category": "B",
        "scenario": "failed",
        "session_index": 0,
        "correct_ratio": 28,  # 28/40 → ajourné
    },
    # Admis — score parfait
    {
        "reference": "GN-CAND-2026-003",
        "first_name": "Alpha",
        "last_name": "Bah",
        "identity_number": "NINA-GN-1999-009012",
        "phone": "+224620111003",
        "permit_category": "B",
        "scenario": "passed",
        "session_index": 0,
        "correct_ratio": 40,  # 40/40 → parfait
    },
    # En attente d'examen — réservé et payé, session future
    {
        "reference": "GN-CAND-2026-004",
        "first_name": "Mariam",
        "last_name": "Soumah",
        "identity_number": "NINA-GN-2003-003456",
        "phone": "+224620111004",
        "permit_category": "B",
        "scenario": "booked_paid",
        "session_index": 1,
    },
    # Réservé uniquement — paiement en attente
    {
        "reference": "GN-CAND-2026-005",
        "first_name": "Ibrahima",
        "last_name": "Kouyaté",
        "identity_number": "NINA-GN-2000-007890",
        "phone": "+224620111005",
        "permit_category": "B",
        "scenario": "booked_pending",
        "session_index": 1,
    },
    # Session Kindia — admis
    {
        "reference": "GN-CAND-2026-006",
        "first_name": "Kadiatou",
        "last_name": "Sylla",
        "identity_number": "NINA-GN-2001-002345",
        "phone": "+224628222001",
        "permit_category": "B",
        "scenario": "passed",
        "session_index": 2,
        "correct_ratio": 36,
    },
    # Candidat sans réservation — inscrit seulement
    {
        "reference": "GN-CAND-2026-007",
        "first_name": "Oumar",
        "last_name": "Baldé",
        "identity_number": "NINA-GN-1998-008901",
        "phone": "+224620111007",
        "permit_category": "B",
        "scenario": "registered_only",
        "session_index": None,
    },
    # Ajourné limite — 34/40 (un de moins que le seuil)
    {
        "reference": "GN-CAND-2026-008",
        "first_name": "Aminata",
        "last_name": "Condé",
        "identity_number": "NINA-GN-2002-006789",
        "phone": "+224620111008",
        "permit_category": "B",
        "scenario": "failed",
        "session_index": 0,
        "correct_ratio": 34,  # 34/40 → ajourné (seuil = 35)
    },
]


def _build_answers(questions: list[Question], correct_ratio: int) -> dict[str, str]:
    """
    Construit un dictionnaire de réponses avec `correct_ratio` bonnes réponses
    et le reste en mauvaises réponses (première option si ≠ bonne réponse).
    """
    answers = {}
    for i, q in enumerate(questions):
        if i < correct_ratio:
            answers[q.id] = q.correct_answer
        else:
            # Choisir la première option qui n'est pas la bonne réponse
            wrong = next((opt for opt in q.options if opt != q.correct_answer), q.options[0])
            answers[q.id] = wrong
    return answers


def seed_candidates_and_flows(
    db,
    sessions: list[ExamSession],
    questions: list[Question],
    admin_user: User,
) -> list[Candidate]:
    candidates = []
    payment_counter = db.query(Payment).count()

    for cdata in CANDIDATES_DATA:
        # Créer ou récupérer le candidat
        cand = db.scalar(select(Candidate).where(Candidate.reference == cdata["reference"]))
        if not cand:
            cand = Candidate(
                reference=cdata["reference"],
                first_name=cdata["first_name"],
                last_name=cdata["last_name"],
                identity_number=cdata["identity_number"],
                phone=cdata["phone"],
                permit_category=cdata["permit_category"],
                status="active",
            )
            db.add(cand)
            db.flush()

        candidates.append(cand)
        scenario = cdata["scenario"]
        sess_idx = cdata.get("session_index")

        if scenario == "registered_only" or sess_idx is None:
            continue

        session = sessions[sess_idx]
        booking_ref = f"GN-BOOK-{cdata['reference']}"
        booking = db.scalar(select(Booking).where(Booking.reference == booking_ref))

        if not booking:
            booking = Booking(
                reference=booking_ref,
                candidate_id=cand.id,
                session_id=session.id,
                status="confirmed",
                verification_code=f"QR-{uuid4().hex[:16].upper()}",
            )
            db.add(booking)
            db.flush()

        # Paiement
        if scenario in ("passed", "failed", "booked_paid"):
            payment_counter += 1
            pay_ref = f"GN-PAY-{cdata['reference']}"
            pay = db.scalar(select(Payment).where(Payment.reference == pay_ref))
            if not pay:
                pay = Payment(
                    reference=pay_ref,
                    booking_reference=booking_ref,
                    amount_gnf=250_000,
                    provider="orange_money",
                    phone=cdata["phone"],
                    status="paid",
                    receipt_number=f"RCPT-{payment_counter:06d}",
                )
                db.add(pay)
                booking.status = "paid"
                db.flush()

        # Examen pour les scénarios terminés
        if scenario in ("passed", "failed"):
            attempt_id = f"ATT-{cdata['reference']}"
            attempt = db.scalar(select(ExamAttempt).where(ExamAttempt.id == attempt_id))
            if not attempt:
                booking.status = "checked_in"
                correct_ratio = cdata.get("correct_ratio", 35)
                answers = _build_answers(questions, correct_ratio)
                import hashlib
                bank_hash = hashlib.sha256(
                    "|".join(f"{q.id}:{q.correct_answer}" for q in questions).encode()
                ).hexdigest()

                now = datetime.now(UTC).replace(tzinfo=None)
                attempt = ExamAttempt(
                    id=attempt_id,
                    candidate_id=cand.id,
                    session_id=session.id,
                    status="submitted",
                    answers=answers,
                    score=correct_ratio,
                    passed=(correct_ratio >= 35),
                    started_at=now - timedelta(minutes=25),
                    submitted_at=now - timedelta(minutes=2),
                )
                db.add(attempt)
                db.flush()

                trace = ExamQuestionTrace(
                    attempt_id=attempt.id,
                    question_ids=[q.id for q in questions],
                    question_count=len(questions),
                    bank_hash=bank_hash,
                    version_label=f"official-bank-{bank_hash[:12]}",
                    selection_mode="active_bank_snapshot",
                )
                db.add(trace)

                # Audit
                db.add(AuditLog(
                    actor_id=admin_user.id,
                    action="exam.submitted",
                    entity="exam_attempt",
                    entity_id=attempt.id,
                    details={
                        "candidate_reference": cand.reference,
                        "score": correct_ratio,
                        "passed": correct_ratio >= 35,
                        "session_reference": session.reference,
                    },
                ))

                # DeviceSession pour traçabilité
                device = DeviceSession(
                    center_id=session.center_id,
                    session_id=session.id,
                    attempt_id=attempt.id,
                    device_key=f"PC-SALLE-{(candidates.index(cand) % 10) + 1:02d}",
                    device_label=f"Poste {(candidates.index(cand) % 10) + 1}",
                    status="active",
                    last_seen_at=now - timedelta(minutes=2),
                )
                db.add(device)

    db.commit()
    for c in candidates:
        db.refresh(c)
    print(f"  ✅ {len(candidates)} candidats avec leurs parcours")
    return candidates


# ── POINT D'ENTRÉE ─────────────────────────────────────────────────────────

def run_seed() -> None:
    _guard()
    init_db()
    db = SessionLocal()
    try:
        print("\n🌱 Seed complet CodeRoute Guinée\n" + "─" * 45)

        print("\n👤 Utilisateurs...")
        users = seed_users(db)

        print("\n🏢 Centres agréés...")
        centers = seed_centers(db)

        print("\n📋 Banque de questions officielle...")
        questions = seed_questions(db)

        print("\n📅 Sessions d'examen...")
        sessions = seed_sessions(db, centers)

        print("\n👥 Candidats et parcours...")
        admin_user = users["super_admin@coderoute.gov.gn"]
        seed_candidates_and_flows(db, sessions, questions, admin_user)

        print("\n" + "─" * 45)
        print("✅ Seed terminé avec succès !\n")
        print("╔══════════════════════════════════════════════════════════════╗")
        print("║              COMPTES DE TEST CODEROUTE GUINÉE               ║")
        print("╠══════════════════════════════════════════════════════════════╣")
        print("║ RÔLE          │ EMAIL                              │ MOT DE PASSE")
        print("╠══════════════════════════════════════════════════════════════╣")
        for u in USERS:
            role = u["role"].ljust(14)
            email = u["email"].ljust(36)
            print(f"║ {role}│ {email}│ {SEED_PASSWORD}")
        print("╚══════════════════════════════════════════════════════════════╝")
        print("\n📊 Données créées :")
        print(f"   • {len(questions)} questions (40 officielles catégorie B)")
        print(f"   • {len(sessions)} sessions planifiées (Conakry ×2, Kindia ×1)")
        print(f"   • {len(CANDIDATES_DATA)} candidats (admis, ajournés, en attente)")
        print("\n📱 Scénarios disponibles :")
        print("   • GN-CAND-2026-001 Mamadou Diallo    → Admis 38/40")
        print("   • GN-CAND-2026-002 Fatoumata Camara  → Ajourné 28/40")
        print("   • GN-CAND-2026-003 Alpha Bah          → Parfait 40/40")
        print("   • GN-CAND-2026-004 Mariam Soumah      → Payé, session dans 14j")
        print("   • GN-CAND-2026-005 Ibrahima Kouyaté   → Réservé, paiement en attente")
        print("   • GN-CAND-2026-006 Kadiatou Sylla      → Admis 36/40 (Kindia)")
        print("   • GN-CAND-2026-007 Oumar Baldé         → Inscrit seulement")
        print("   • GN-CAND-2026-008 Aminata Condé       → Ajourné 34/40 (limite)")

    finally:
        db.close()


if __name__ == "__main__":
    run_seed()
