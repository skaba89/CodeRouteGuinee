"""
seed_demo_dntt.py — Environnement de démonstration DNTT
════════════════════════════════════════════════════════

S'appuie sur seed_full (comptes, 135 centres, banque de 200 questions,
sessions, 8 candidats scénarisés) puis ajoute ce qu'une démonstration devant
la DNTT exige :

  - un compte de démonstration par rôle (dont auto-école et candidats) ;
  - des médias d'illustration HTTPS sur la banque, pour que l'examen officiel
    passe la garde média (photos routières réelles, voir ATTRIBUTION.md) ;
  - trois mois d'activité nationale (8 régions) : identités, réservations,
    paiements Mobile Money, examens, incidents, journal d'audit ;
  - une session « en direct » au centre de Kaloum, positionnée pour que le
    contrôle d'entrée et le démarrage de l'examen soient ouverts pendant la
    démonstration.

Les données sont fictives et la banque n'est PAS homologuée DNTT.

Usage :
    python -m app.seed_demo_dntt                  # seed complet + session live dans 15 min
    python -m app.seed_demo_dntt --live-in 10     # session live dans 10 min
    python -m app.seed_demo_dntt --live-only      # ajoute uniquement une nouvelle session live

Bloqué hors ENVIRONMENT=development, sauf ALLOW_DEMO_SEED_NON_DEV=true sur une
base jetable (même garde que seed_full).
"""
from __future__ import annotations

import argparse
import hashlib
import os
import random
from datetime import UTC, datetime, timedelta
from urllib.parse import urlparse
from uuid import uuid4

from sqlalchemy import func, select

from app.db.session import SessionLocal, init_db
from app.models_audit import AuditLog
from app.models_booking import Booking
from app.models_candidate import Candidate
from app.models_candidate_identity import CandidateIdentityCheck
from app.models_center import Center
from app.models_center_incident import CenterIncident
from app.models_center_station import CenterStation
from app.models_exam_attempt import ExamAttempt
from app.models_exam_question_trace import ExamQuestionTrace
from app.models_payment import Payment
from app.models_question import Question
from app.models_session import ExamSession
from app.models_user import User
from app.question_bank_gn import QUESTIONS_GN
from app.security import get_password_hash
from app.seed_full import (
    SEED_PASSWORD,
    USERS,
    _build_answers,
    _guard,
    assign_center_users,
    seed_candidates_and_flows,
    seed_centers,
    seed_questions,
    seed_sessions,
    seed_users,
)
from app.tarifs import get_tarif_for_candidate
from app.territory import region_for_prefecture

LIVE_CENTER_CODE = "CRG-KAL-001"
DEMO_REFERENCE_PREFIX = "GN-DEMO-"
DEFAULT_MEDIA_BASE_URL = "https://coderouteguinee-frontend.onrender.com/media/exam/guinea/realistic/"

# Comptes ajoutés à ceux de seed_full (même mot de passe de démonstration).
DEMO_ACCOUNTS = [
    {
        "email": "auto-ecole.kaloum@coderoute.gov.gn",
        "full_name": "Auto-école La Prudence — Kaloum",
        "role": "driving_school",
    },
    {
        "email": "mamadou.diallo@demo.coderoute.gn",
        "full_name": "Mamadou Diallo",
        "role": "candidate",
        "candidate_reference": "GN-CAND-2026-001",
    },
    {
        "email": "mariam.soumah@demo.coderoute.gn",
        "full_name": "Mariam Soumah",
        "role": "candidate",
        "candidate_reference": "GN-CAND-2026-004",
    },
]

# Photos routières réelles (Wikimedia Commons, CC BY / CC BY-SA). Les questions
# de la banque sont rédigées pour se suffire à elles-mêmes : l'image illustre
# le contexte, le texte alternatif décrit fidèlement la photo.
_ROAD_SIGNS = ("road-signs-conakry-coyah.webp",
               "Panneau de chantier « Travaux — Aucune entrée » au bord d'une piste, route Conakry–Coyah")
_STREET = ("roundabout-enta-conakry.webp",
           "Rue animée à Enta (Conakry) : voitures, motos et piétons partagent la chaussée")
_ROAD = ("route-coyah.webp",
         "Route bitumée à deux voies bordée de végétation, préfecture de Coyah")
_TRUCKS = ("traffic-conakry-boke.webp",
           "Voiture circulant derrière des camions chargés sur la route Conakry–Boké")

CATEGORY_MEDIA: dict[str, tuple[str, str]] = {
    "signalisation": _ROAD_SIGNS,
    "priorites": _STREET,
    "vitesse": _ROAD,
    "depassement": _TRUCKS,
    "securite_passive": _TRUCKS,
    "urgence": _ROAD,
    "alcool_drogues": _STREET,
    "premiers_secours": _STREET,
}

# Taux de réussite cibles par région (données fictives de démonstration).
REGION_PASS_RATE = {
    "Conakry": 0.68,
    "Kindia": 0.64,
    "Boké": 0.58,
    "Labé": 0.62,
    "Mamou": 0.60,
    "Faranah": 0.55,
    "Kankan": 0.57,
    "N'Zérékoré": 0.53,
}

PROVIDER_WEIGHTS = (("orange_money", 55), ("mtn_money", 25), ("wave", 15), ("paydunya", 5))

# Centre au profil volontairement anormal, pour montrer la surveillance
# statistique : réussite quasi systématique, candidats venus de Conakry,
# un examen démarré hors créneau. Données fictives.
ANOMALOUS_CENTER_CODE = "CRG-SIGUIR-002"

FIRST_NAMES = (
    "Mamadou", "Fatoumata", "Alpha", "Mariama", "Ibrahima", "Aïssatou", "Ousmane", "Kadiatou",
    "Abdoulaye", "Hawa", "Sékou", "Djénabou", "Mohamed", "Aminata", "Thierno", "Fanta",
    "Lansana", "Nènè", "Boubacar", "Mariam", "Moussa", "Hadja", "Saliou", "Kadija",
)
LAST_NAMES = (
    "Diallo", "Camara", "Bah", "Sylla", "Soumah", "Barry", "Condé", "Keïta", "Touré", "Kouyaté",
    "Baldé", "Cissé", "Sow", "Kaba", "Bangoura", "Fofana", "Traoré", "Doumbouya", "Koné", "Loua",
)


def _now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


# ── Comptes ────────────────────────────────────────────────────────────────

def seed_demo_accounts(db) -> dict[str, User]:
    accounts: dict[str, User] = {}
    for spec in DEMO_ACCOUNTS:
        user = db.scalar(select(User).where(User.email == spec["email"]))
        if user is None:
            user = User(
                email=spec["email"],
                full_name=spec["full_name"],
                password_hash=get_password_hash(SEED_PASSWORD),
                role=spec["role"],
                is_active=True,
            )
            db.add(user)
            db.flush()
        accounts[spec["email"]] = user

        reference = spec.get("candidate_reference")
        if reference:
            candidate = db.scalar(select(Candidate).where(Candidate.reference == reference))
            if candidate is not None and candidate.user_id is None:
                candidate.user_id = user.id
                candidate.email = spec["email"]
    db.commit()
    return accounts


# ── Médias d'illustration ──────────────────────────────────────────────────

def _media_base_url() -> str:
    base = os.getenv("DEMO_MEDIA_BASE_URL", DEFAULT_MEDIA_BASE_URL).strip()
    parsed = urlparse(base)
    if parsed.scheme != "https" or not parsed.netloc:
        # La garde d'examen n'accepte que des médias HTTPS : échouer tôt plutôt
        # que produire une banque qui bloquera l'examen en pleine démonstration.
        raise RuntimeError(f"DEMO_MEDIA_BASE_URL doit être une URL HTTPS (reçu : {base!r})")
    return base if base.endswith("/") else base + "/"


def apply_demo_media(db) -> int:
    """Pose une illustration HTTPS sur les questions sans média exploitable.

    Une question qui porte déjà une image ou une vidéo HTTPS n'est pas touchée.
    """
    base = _media_base_url()
    updated = 0
    for question in db.scalars(select(Question).where(Question.is_active.is_(True))).all():
        current_url = (question.media_url or "").strip()
        if question.media_type in {"image", "video"} and current_url.startswith("https://") and question.media_alt:
            continue
        filename, alt = CATEGORY_MEDIA.get(question.category, _ROAD)
        question.media_type = "image"
        question.media_url = base + filename
        question.media_alt = alt
        updated += 1
    db.commit()
    return updated


# ── Activité nationale ─────────────────────────────────────────────────────

def _official_questions(db) -> list[Question]:
    texts = {row["text"] for row in QUESTIONS_GN}
    questions = [q for q in db.scalars(select(Question)).all() if q.text in texts]
    return sorted(questions, key=lambda q: q.text)


def _verify_identity(db, candidate: Candidate, actor: User, when: datetime) -> None:
    db.add(CandidateIdentityCheck(
        candidate_id=candidate.id,
        document_type="national_id",
        document_reference=f"CNI-{candidate.identity_number}",
        status="verified",
        verified_by_id=actor.id,
        decision_reason="Carte d'identité contrôlée au guichet",
        created_at=when,
        decided_at=when + timedelta(minutes=12),
    ))
    candidate.status = "verified"


def _pick_provider(rng: random.Random) -> str:
    return rng.choices([p for p, _ in PROVIDER_WEIGHTS], weights=[w for _, w in PROVIDER_WEIGHTS])[0]


def _guinean_phone(rng: random.Random) -> str:
    return f"+224{rng.choice(('620', '621', '622', '624', '625', '628', '655', '660', '664'))}{rng.randint(100000, 999999)}"


def seed_national_activity(
    db,
    admin: User,
    school: User,
    *,
    scale: float = 1.0,
    center_limit: int | None = None,
) -> dict[str, int]:
    """Trois mois d'activité fictive sur les centres agréés, idempotent.

    `center_limit` borne le nombre de centres alimentés (tests).
    """
    already = db.scalar(
        select(func.count(Candidate.id)).where(Candidate.reference.like(f"{DEMO_REFERENCE_PREFIX}%"))
    )
    if already:
        return {"candidates": int(already), "created": 0}

    rng = random.Random(2026)
    now = _now()
    questions = _official_questions(db)
    bank_hash = hashlib.sha256(
        "|".join(f"{q.id}:{q.correct_answer}" for q in questions).encode()
    ).hexdigest()
    price = get_tarif_for_candidate("B", 1)
    centers = list(db.scalars(select(Center).where(Center.status.in_(("active", "accredited")))).all())

    counter = 0
    stats = {"candidates": 0, "attempts": 0, "payments": 0, "pending_payments": 0}

    for center in sorted(centers, key=lambda c: c.code)[:center_limit]:
        region = region_for_prefecture(center.prefecture)
        anomalous = center.code == ANOMALOUS_CENTER_CODE
        pass_rate = 0.97 if anomalous else REGION_PASS_RATE.get(region, 0.58)
        n_sessions = 4 if anomalous else 3 if region == "Conakry" else 2
        days = sorted(rng.sample(range(4, 90), n_sessions), reverse=True)

        for day in days:
            starts_at = (now - timedelta(days=day)).replace(
                hour=rng.choice((8, 10, 14)), minute=0, second=0, microsecond=0,
            )
            session = ExamSession(
                reference=f"GN-SESSION-DEMO-{center.code[4:]}-{starts_at:%Y%m%d}",
                center_id=center.id,
                starts_at=starts_at,
                capacity=35,
                status="closed",
                created_at=starts_at - timedelta(days=10),
            )
            db.add(session)
            db.flush()

            for seat in range(max(3, int(rng.randint(10, 12) if anomalous else rng.randint(5, 12) * scale))):
                counter += 1
                first, last = rng.choice(FIRST_NAMES), rng.choice(LAST_NAMES)
                registered_at = starts_at - timedelta(days=rng.randint(6, 20))
                candidate = Candidate(
                    reference=f"{DEMO_REFERENCE_PREFIX}{counter:05d}",
                    first_name=first,
                    last_name=last,
                    identity_number=f"GN{rng.randint(10**9, 10**10 - 1)}",
                    phone=_guinean_phone(rng),
                    permit_category="B",
                    city="Conakry" if anomalous else center.city,
                    status="registered",
                    registered_by=school.id if region == "Conakry" and rng.random() < 0.3 else None,
                    created_at=registered_at,
                )
                db.add(candidate)
                db.flush()
                _verify_identity(db, candidate, admin, registered_at + timedelta(hours=2))
                stats["candidates"] += 1

                booking = Booking(
                    reference=f"GN-BOOK-DEMO-{counter:05d}",
                    candidate_id=candidate.id,
                    session_id=session.id,
                    status="confirmed",
                    verification_code=f"GN-VERIFY-DEMO-{uuid4().hex[:20].upper()}",
                    created_at=registered_at + timedelta(days=1),
                )
                db.add(booking)

                provider = _pick_provider(rng)
                paid = rng.random() > 0.03
                payment = Payment(
                    reference=f"GN-PAY-DEMO-{counter:05d}",
                    booking_reference=booking.reference,
                    amount_gnf=price,
                    provider=provider,
                    phone=candidate.phone,
                    status="paid" if paid else "pending",
                    receipt_number=f"GN-RECEIPT-DEMO-{counter:05d}",
                    external_reference=f"SANDBOX-{provider.upper()}-{counter:05d}",
                    paid_at=booking.created_at + timedelta(minutes=4) if paid else None,
                    created_at=booking.created_at + timedelta(minutes=3),
                )
                db.add(payment)
                if not paid:
                    stats["pending_payments"] += 1
                    continue
                stats["payments"] += 1
                booking.status = "checked_in"
                booking.payment_reference = payment.reference

                passed = rng.random() < pass_rate
                score = rng.randint(35, 40) if passed else rng.randint(22, 34)
                # Un examen du centre anormal démarre 2 h après le début de session.
                started_at = starts_at + timedelta(minutes=125 if anomalous and seat == 0 else 5)
                attempt = ExamAttempt(
                    candidate_id=candidate.id,
                    session_id=session.id,
                    status="submitted",
                    answers=_build_answers(questions, score),
                    score=score,
                    passed=passed,
                    started_at=started_at,
                    submitted_at=started_at + timedelta(minutes=rng.randint(13, 25)),
                )
                db.add(attempt)
                db.flush()
                candidate.attempt_count = 1
                db.add(ExamQuestionTrace(
                    attempt_id=attempt.id,
                    question_ids=[q.id for q in questions],
                    question_count=len(questions),
                    bank_hash=bank_hash,
                    version_label=f"official-bank-{bank_hash[:12]}",
                    selection_mode="active_bank_snapshot",
                ))
                db.add(AuditLog(
                    actor_id=admin.id,
                    action="exam.submitted",
                    entity="exam_attempt",
                    entity_id=attempt.id,
                    details={
                        "candidate_reference": candidate.reference,
                        "score": score,
                        "passed": passed,
                        "session_reference": session.reference,
                        "center_code": center.code,
                    },
                    created_at=attempt.submitted_at,
                ))
                stats["attempts"] += 1
        db.commit()

    return {**stats, "created": stats["candidates"]}


def seed_incidents_and_stations(db, admin: User) -> None:
    if db.scalar(select(func.count(CenterIncident.id))):
        return
    now = _now()
    by_code = {c.code: c for c in db.scalars(select(Center)).all()}
    incidents = [
        ("CRG-NZEREK-001", "power_outage", "high", "open",
         "Coupure d'électricité pendant la session du matin ; 6 postes arrêtés, examens suspendus.", None),
        ("CRG-KANKAN-002", "technical_issue", "medium", "open",
         "Connexion internet instable : synchronisation des résultats différée.", None),
        ("CRG-KINDIA-001", "identity_dispute", "medium", "resolved",
         "Candidat présentant une pièce d'identité au nom d'un tiers ; entrée refusée.",
         "Signalement transmis à la DNTT, réservation annulée."),
        ("CRG-LABE-001", "technical_issue", "low", "resolved",
         "Poste n°4 bloqué au démarrage.", "Poste redémarré, candidat replacé sur le poste n°7."),
    ]
    for code, kind, severity, status, description, resolution in incidents:
        center = by_code.get(code)
        if center is None:
            continue
        created = now - timedelta(days=random.Random(code).randint(1, 20))
        db.add(CenterIncident(
            center_id=center.id,
            incident_type=kind,
            severity=severity,
            status=status,
            description=description,
            resolution_notes=resolution,
            reported_by_id=admin.id,
            resolved_by_id=admin.id if status == "resolved" else None,
            created_at=created,
            resolved_at=created + timedelta(hours=3) if status == "resolved" else None,
        ))

    # Registre de postes pour quelques centres de l'intérieur. Le centre de la
    # session live n'en a pas : un registre rend le device_key obligatoire au
    # démarrage de l'examen, ce que le navigateur de démonstration n'a pas.
    for code in ("CRG-KINDIA-001", "CRG-LABE-001", "CRG-KANKAN-001"):
        center = by_code.get(code)
        if center is None:
            continue
        for index in range(1, 9):
            db.add(CenterStation(
                center_id=center.id,
                device_key=f"{code}-PC-{index:02d}",
                label=f"Poste {index}",
                room="Salle A",
                status="active" if index != 8 else "maintenance",
                created_by_id=admin.id,
            ))
    db.commit()


def verify_seeded_candidates(db, admin: User) -> None:
    """Les candidats scénarisés de seed_full doivent pouvoir être contrôlés au centre."""
    for candidate in db.scalars(select(Candidate).where(Candidate.reference.like("GN-CAND-2026-%"))).all():
        has_check = db.scalar(
            select(CandidateIdentityCheck.id).where(
                CandidateIdentityCheck.candidate_id == candidate.id,
                CandidateIdentityCheck.status == "verified",
            )
        )
        if not has_check:
            _verify_identity(db, candidate, admin, (candidate.created_at or _now()))
    db.commit()


# ── Session live ───────────────────────────────────────────────────────────

def create_live_session(db, minutes_from_now: int) -> ExamSession:
    center = db.scalar(select(Center).where(Center.code == LIVE_CENTER_CODE))
    if center is None:
        raise RuntimeError(f"Centre {LIVE_CENTER_CODE} absent : lancer d'abord le seed complet")
    starts_at = (_now() + timedelta(minutes=minutes_from_now)).replace(second=0, microsecond=0)
    reference = f"GN-SESSION-DEMO-LIVE-{starts_at:%Y%m%d-%H%M}"
    existing = db.scalar(select(ExamSession).where(ExamSession.reference == reference))
    if existing is not None:
        return existing
    session = ExamSession(
        reference=reference,
        center_id=center.id,
        starts_at=starts_at,
        capacity=20,
        status="planned",
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def _print_live_windows(session: ExamSession) -> None:
    from app.core.config import get_settings

    settings = get_settings()
    start = session.starts_at
    checkin = (start - timedelta(minutes=settings.exam_checkin_open_minutes_before),
               start + timedelta(minutes=settings.exam_checkin_close_minutes_after))
    exam = (start - timedelta(minutes=settings.exam_start_open_minutes_before),
            start + timedelta(minutes=settings.exam_start_close_minutes_after))
    print(f"\n🎬 Session live : {session.reference} — centre {LIVE_CENTER_CODE}")
    print(f"   Début (UTC = heure de Conakry) : {start:%H:%M}")
    print(f"   Contrôle d'entrée ouvert       : {checkin[0]:%H:%M} → {checkin[1]:%H:%M}")
    print(f"   Démarrage examen ouvert        : {exam[0]:%H:%M} → {exam[1]:%H:%M}")


# ── Point d'entrée ─────────────────────────────────────────────────────────

def run(*, live_in: int, live_only: bool, scale: float) -> None:
    _guard()
    init_db()
    db = SessionLocal()
    try:
        if not live_only:
            print("\n🇬🇳 Environnement de démonstration DNTT\n" + "─" * 45)
            users = seed_users(db)
            centers = seed_centers(db)
            assign_center_users(db, users, centers)
            questions = seed_questions(db)
            sessions = seed_sessions(db, centers)
            admin = users["super_admin@coderoute.gov.gn"]
            seed_candidates_and_flows(db, sessions, questions, admin)

            accounts = seed_demo_accounts(db)
            print(f"  ✅ {apply_demo_media(db)} questions illustrées (médias HTTPS)")
            verify_seeded_candidates(db, admin)
            activity = seed_national_activity(
                db, admin, accounts["auto-ecole.kaloum@coderoute.gov.gn"], scale=scale,
            )
            print(f"  ✅ Activité nationale : {activity}")
            seed_incidents_and_stations(db, admin)

        session = create_live_session(db, live_in)
        _print_live_windows(session)

        if not live_only:
            print("\n🔑 Comptes de démonstration (mot de passe : " + SEED_PASSWORD + ")")
            for spec in [*USERS, *DEMO_ACCOUNTS]:
                print(f"   {spec['role']:<15} {spec['email']}")
            print("\n⚠️  Données fictives — banque de questions de démonstration, non homologuée DNTT.")
    finally:
        db.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed de démonstration DNTT")
    parser.add_argument("--live-in", type=int, default=15,
                        help="minutes avant le début de la session live (défaut : 15)")
    parser.add_argument("--live-only", action="store_true",
                        help="n'ajoute qu'une nouvelle session live")
    parser.add_argument("--scale", type=float, default=1.0,
                        help="facteur de volume de l'activité nationale (défaut : 1.0)")
    args = parser.parse_args()
    run(live_in=args.live_in, live_only=args.live_only, scale=args.scale)


if __name__ == "__main__":
    main()
