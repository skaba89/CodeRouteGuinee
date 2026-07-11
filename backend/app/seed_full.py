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
from app.question_bank_gn import QUESTIONS_GN, QUESTIONS_TRAINING_FULL
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
        "code": "CRG-KAL-001",
        "name": "Centre d'Examen du Code de la Route \u2014 Kaloum 1",
        "city": "Conakry",
        "commune": "Kaloum",
        "prefecture": "Conakry",
        "address": "Quartier Kaloum-1, Conakry",
        "latitude": 9.535,
        "longitude": -13.6773,
        "capacity": 35,
        "max_sessions_per_week": 3,
        "status": "accredited",
    },
    {
        "code": "CRG-KAL-002",
        "name": "Centre d'Examen du Code de la Route \u2014 Kaloum 2",
        "city": "Conakry",
        "commune": "Kaloum",
        "prefecture": "Conakry",
        "address": "Quartier Kaloum-2, Conakry",
        "latitude": 9.54,
        "longitude": -13.6743,
        "capacity": 35,
        "max_sessions_per_week": 3,
        "status": "accredited",
    },
    {
        "code": "CRG-KAL-003",
        "name": "Centre d'Examen du Code de la Route \u2014 Kaloum 3",
        "city": "Conakry",
        "commune": "Kaloum",
        "prefecture": "Conakry",
        "address": "Quartier Kaloum-3, Conakry",
        "latitude": 9.545,
        "longitude": -13.6713,
        "capacity": 35,
        "max_sessions_per_week": 3,
        "status": "accredited",
    },
    {
        "code": "CRG-DIX-001",
        "name": "Centre d'Examen du Code de la Route \u2014 Dixinn 1",
        "city": "Conakry",
        "commune": "Dixinn",
        "prefecture": "Conakry",
        "address": "Quartier Dixinn-1, Conakry",
        "latitude": 9.543,
        "longitude": -13.6519,
        "capacity": 35,
        "max_sessions_per_week": 3,
        "status": "accredited",
    },
    {
        "code": "CRG-DIX-002",
        "name": "Centre d'Examen du Code de la Route \u2014 Dixinn 2",
        "city": "Conakry",
        "commune": "Dixinn",
        "prefecture": "Conakry",
        "address": "Quartier Dixinn-2, Conakry",
        "latitude": 9.548,
        "longitude": -13.6489,
        "capacity": 35,
        "max_sessions_per_week": 3,
        "status": "accredited",
    },
    {
        "code": "CRG-DIX-003",
        "name": "Centre d'Examen du Code de la Route \u2014 Dixinn 3",
        "city": "Conakry",
        "commune": "Dixinn",
        "prefecture": "Conakry",
        "address": "Quartier Dixinn-3, Conakry",
        "latitude": 9.553,
        "longitude": -13.6459,
        "capacity": 35,
        "max_sessions_per_week": 3,
        "status": "accredited",
    },
    {
        "code": "CRG-RAT-001",
        "name": "Centre d'Examen du Code de la Route \u2014 Ratoma 1",
        "city": "Conakry",
        "commune": "Ratoma",
        "prefecture": "Conakry",
        "address": "Quartier Ratoma-1, Conakry",
        "latitude": 9.5837,
        "longitude": -13.6231,
        "capacity": 35,
        "max_sessions_per_week": 3,
        "status": "accredited",
    },
    {
        "code": "CRG-RAT-002",
        "name": "Centre d'Examen du Code de la Route \u2014 Ratoma 2",
        "city": "Conakry",
        "commune": "Ratoma",
        "prefecture": "Conakry",
        "address": "Quartier Ratoma-2, Conakry",
        "latitude": 9.5887,
        "longitude": -13.6201,
        "capacity": 35,
        "max_sessions_per_week": 3,
        "status": "accredited",
    },
    {
        "code": "CRG-RAT-003",
        "name": "Centre d'Examen du Code de la Route \u2014 Ratoma 3",
        "city": "Conakry",
        "commune": "Ratoma",
        "prefecture": "Conakry",
        "address": "Quartier Ratoma-3, Conakry",
        "latitude": 9.5937,
        "longitude": -13.6171,
        "capacity": 35,
        "max_sessions_per_week": 3,
        "status": "accredited",
    },
    {
        "code": "CRG-MAT-001",
        "name": "Centre d'Examen du Code de la Route \u2014 Matam 1",
        "city": "Conakry",
        "commune": "Matam",
        "prefecture": "Conakry",
        "address": "Quartier Matam-1, Conakry",
        "latitude": 9.5536,
        "longitude": -13.658,
        "capacity": 35,
        "max_sessions_per_week": 3,
        "status": "accredited",
    },
    {
        "code": "CRG-MAT-002",
        "name": "Centre d'Examen du Code de la Route \u2014 Matam 2",
        "city": "Conakry",
        "commune": "Matam",
        "prefecture": "Conakry",
        "address": "Quartier Matam-2, Conakry",
        "latitude": 9.5586,
        "longitude": -13.655,
        "capacity": 35,
        "max_sessions_per_week": 3,
        "status": "accredited",
    },
    {
        "code": "CRG-MAT-003",
        "name": "Centre d'Examen du Code de la Route \u2014 Matam 3",
        "city": "Conakry",
        "commune": "Matam",
        "prefecture": "Conakry",
        "address": "Quartier Matam-3, Conakry",
        "latitude": 9.5636,
        "longitude": -13.652,
        "capacity": 35,
        "max_sessions_per_week": 3,
        "status": "accredited",
    },
    {
        "code": "CRG-MTO-001",
        "name": "Centre d'Examen du Code de la Route \u2014 Matoto 1",
        "city": "Conakry",
        "commune": "Matoto",
        "prefecture": "Conakry",
        "address": "Quartier Matoto-1, Conakry",
        "latitude": 9.4945,
        "longitude": -13.6285,
        "capacity": 35,
        "max_sessions_per_week": 3,
        "status": "accredited",
    },
    {
        "code": "CRG-MTO-002",
        "name": "Centre d'Examen du Code de la Route \u2014 Matoto 2",
        "city": "Conakry",
        "commune": "Matoto",
        "prefecture": "Conakry",
        "address": "Quartier Matoto-2, Conakry",
        "latitude": 9.4995,
        "longitude": -13.6255,
        "capacity": 35,
        "max_sessions_per_week": 3,
        "status": "accredited",
    },
    {
        "code": "CRG-MTO-003",
        "name": "Centre d'Examen du Code de la Route \u2014 Matoto 3",
        "city": "Conakry",
        "commune": "Matoto",
        "prefecture": "Conakry",
        "address": "Quartier Matoto-3, Conakry",
        "latitude": 9.5045,
        "longitude": -13.6225,
        "capacity": 35,
        "max_sessions_per_week": 3,
        "status": "accredited",
    },
    {
        "code": "CRG-LAM-001",
        "name": "Centre d'Examen du Code de la Route — Lambanyi 1",
        "city": "Conakry",
        "commune": "Lambanyi",
        "prefecture": "Conakry",
        "address": "Quartier Lambanyi-Cité, Conakry",
        "capacity": 35,
        "max_sessions_per_week": 3,
        "status": "accredited",
    },
    {
        "code": "CRG-LAM-002",
        "name": "Centre d'Examen du Code de la Route — Lambanyi 2",
        "city": "Conakry",
        "commune": "Lambanyi",
        "prefecture": "Conakry",
        "address": "Quartier Lambanyi-Marché, Conakry",
        "capacity": 35,
        "max_sessions_per_week": 3,
        "status": "accredited",
    },
    {
        "code": "CRG-LAM-003",
        "name": "Centre d'Examen du Code de la Route — Lambanyi 3",
        "city": "Conakry",
        "commune": "Lambanyi",
        "prefecture": "Conakry",
        "address": "Quartier Lambanyi-Nongo Route, Conakry",
        "capacity": 35,
        "max_sessions_per_week": 3,
        "status": "accredited",
    },
    {
        "code": "CRG-GBS-001",
        "name": "Centre d'Examen du Code de la Route — Gbessia 1",
        "city": "Conakry",
        "commune": "Gbessia",
        "prefecture": "Conakry",
        "address": "Quartier Gbessia-Aéroport, Conakry",
        "capacity": 35,
        "max_sessions_per_week": 3,
        "status": "accredited",
    },
    {
        "code": "CRG-GBS-002",
        "name": "Centre d'Examen du Code de la Route — Gbessia 2",
        "city": "Conakry",
        "commune": "Gbessia",
        "prefecture": "Conakry",
        "address": "Quartier Gbessia-Port, Conakry",
        "capacity": 35,
        "max_sessions_per_week": 3,
        "status": "accredited",
    },
    {
        "code": "CRG-GBS-003",
        "name": "Centre d'Examen du Code de la Route — Gbessia 3",
        "city": "Conakry",
        "commune": "Gbessia",
        "prefecture": "Conakry",
        "address": "Quartier Gbessia-Enco 5, Conakry",
        "capacity": 35,
        "max_sessions_per_week": 3,
        "status": "accredited",
    },
    {
        "code": "CRG-SON-001",
        "name": "Centre d'Examen du Code de la Route — Sonfonia 1",
        "city": "Conakry",
        "commune": "Sonfonia",
        "prefecture": "Conakry",
        "address": "Quartier Sonfonia-Gare, Conakry",
        "capacity": 35,
        "max_sessions_per_week": 3,
        "status": "accredited",
    },
    {
        "code": "CRG-SON-002",
        "name": "Centre d'Examen du Code de la Route — Sonfonia 2",
        "city": "Conakry",
        "commune": "Sonfonia",
        "prefecture": "Conakry",
        "address": "Quartier Sonfonia-Cimenterie, Conakry",
        "capacity": 35,
        "max_sessions_per_week": 3,
        "status": "accredited",
    },
    {
        "code": "CRG-SON-003",
        "name": "Centre d'Examen du Code de la Route — Sonfonia 3",
        "city": "Conakry",
        "commune": "Sonfonia",
        "prefecture": "Conakry",
        "address": "Quartier Sonfonia-Bambeto, Conakry",
        "capacity": 35,
        "max_sessions_per_week": 3,
        "status": "accredited",
    },
    {
        "code": "CRG-TOM-001",
        "name": "Centre d'Examen du Code de la Route — Tombolia 1",
        "city": "Conakry",
        "commune": "Tombolia",
        "prefecture": "Conakry",
        "address": "Quartier Tombolia-Centre, Conakry",
        "capacity": 35,
        "max_sessions_per_week": 3,
        "status": "accredited",
    },
    {
        "code": "CRG-TOM-002",
        "name": "Centre d'Examen du Code de la Route — Tombolia 2",
        "city": "Conakry",
        "commune": "Tombolia",
        "prefecture": "Conakry",
        "address": "Quartier Tombolia-Hafia, Conakry",
        "capacity": 35,
        "max_sessions_per_week": 3,
        "status": "accredited",
    },
    {
        "code": "CRG-TOM-003",
        "name": "Centre d'Examen du Code de la Route — Tombolia 3",
        "city": "Conakry",
        "commune": "Tombolia",
        "prefecture": "Conakry",
        "address": "Quartier Tombolia-Yimbaya, Conakry",
        "capacity": 35,
        "max_sessions_per_week": 3,
        "status": "accredited",
    },
    {
        "code": "CRG-KAK-001",
        "name": "Centre d'Examen du Code de la Route — Kakimbo 1",
        "city": "Conakry",
        "commune": "Kakimbo",
        "prefecture": "Conakry",
        "address": "Quartier Kakimbo-Est, Conakry",
        "capacity": 35,
        "max_sessions_per_week": 3,
        "status": "accredited",
    },
    {
        "code": "CRG-KAK-002",
        "name": "Centre d'Examen du Code de la Route — Kakimbo 2",
        "city": "Conakry",
        "commune": "Kakimbo",
        "prefecture": "Conakry",
        "address": "Quartier Kakimbo-Ouest, Conakry",
        "capacity": 35,
        "max_sessions_per_week": 3,
        "status": "accredited",
    },
    {
        "code": "CRG-KAK-003",
        "name": "Centre d'Examen du Code de la Route — Kakimbo 3",
        "city": "Conakry",
        "commune": "Kakimbo",
        "prefecture": "Conakry",
        "address": "Quartier Kakimbo-Centre, Conakry",
        "capacity": 35,
        "max_sessions_per_week": 3,
        "status": "accredited",
    },
    {
        "code": "CRG-KOL-001",
        "name": "Centre d'Examen du Code de la Route — Koloma 1",
        "city": "Conakry",
        "commune": "Koloma",
        "prefecture": "Conakry",
        "address": "Quartier Koloma-Est, Conakry",
        "capacity": 35,
        "max_sessions_per_week": 3,
        "status": "accredited",
    },
    {
        "code": "CRG-KOL-002",
        "name": "Centre d'Examen du Code de la Route — Koloma 2",
        "city": "Conakry",
        "commune": "Koloma",
        "prefecture": "Conakry",
        "address": "Quartier Koloma-Centre, Conakry",
        "capacity": 35,
        "max_sessions_per_week": 3,
        "status": "accredited",
    },
    {
        "code": "CRG-KOL-003",
        "name": "Centre d'Examen du Code de la Route — Koloma 3",
        "city": "Conakry",
        "commune": "Koloma",
        "prefecture": "Conakry",
        "address": "Quartier Koloma-Ouest, Conakry",
        "capacity": 35,
        "max_sessions_per_week": 3,
        "status": "accredited",
    },
    {
        "code": "CRG-NON-001",
        "name": "Centre d'Examen du Code de la Route — Nongo 1",
        "city": "Conakry",
        "commune": "Nongo",
        "prefecture": "Conakry",
        "address": "Quartier Nongo-Centre, Conakry",
        "capacity": 35,
        "max_sessions_per_week": 3,
        "status": "accredited",
    },
    {
        "code": "CRG-NON-002",
        "name": "Centre d'Examen du Code de la Route — Nongo 2",
        "city": "Conakry",
        "commune": "Nongo",
        "prefecture": "Conakry",
        "address": "Quartier Nongo-Cité Ministérielle, Conakry",
        "capacity": 35,
        "max_sessions_per_week": 3,
        "status": "accredited",
    },
    {
        "code": "CRG-NON-003",
        "name": "Centre d'Examen du Code de la Route — Nongo 3",
        "city": "Conakry",
        "commune": "Nongo",
        "prefecture": "Conakry",
        "address": "Quartier Nongo-Kipé, Conakry",
        "capacity": 35,
        "max_sessions_per_week": 3,
        "status": "accredited",
    },
    {
        "code": "CRG-COS-001",
        "name": "Centre d'Examen du Code de la Route — Cosa 1",
        "city": "Conakry",
        "commune": "Cosa",
        "prefecture": "Conakry",
        "address": "Quartier Cosa-Wanindara, Conakry",
        "capacity": 35,
        "max_sessions_per_week": 3,
        "status": "accredited",
    },
    {
        "code": "CRG-COS-002",
        "name": "Centre d'Examen du Code de la Route — Cosa 2",
        "city": "Conakry",
        "commune": "Cosa",
        "prefecture": "Conakry",
        "address": "Quartier Cosa-Bonfi, Conakry",
        "capacity": 35,
        "max_sessions_per_week": 3,
        "status": "accredited",
    },
    {
        "code": "CRG-COS-003",
        "name": "Centre d'Examen du Code de la Route — Cosa 3",
        "city": "Conakry",
        "commune": "Cosa",
        "prefecture": "Conakry",
        "address": "Quartier Cosa-Madina, Conakry",
        "capacity": 35,
        "max_sessions_per_week": 3,
        "status": "accredited",
    },
    {
        "code": "CRG-BOFFA-001",
        "name": "Centre d'Examen du Code de la Route \u2014 Boffa 1",
        "city": "Boffa",
        "commune": "Boffa-Centre",
        "prefecture": "Boffa",
        "address": "Quartier 1, Boffa",
        "latitude": 10.1833,
        "longitude": -14.0333,
        "capacity": 35,
        "max_sessions_per_week": 3,
        "status": "accredited",
    },
    {
        "code": "CRG-BOFFA-002",
        "name": "Centre d'Examen du Code de la Route \u2014 Boffa 2",
        "city": "Boffa",
        "commune": "Boffa-Centre",
        "prefecture": "Boffa",
        "address": "Quartier 2, Boffa",
        "latitude": 10.1913,
        "longitude": -14.0283,
        "capacity": 35,
        "max_sessions_per_week": 3,
        "status": "accredited",
    },
    {
        "code": "CRG-BOFFA-003",
        "name": "Centre d'Examen du Code de la Route \u2014 Boffa 3",
        "city": "Boffa",
        "commune": "Boffa-Centre",
        "prefecture": "Boffa",
        "address": "Quartier 3, Boffa",
        "latitude": 10.1993,
        "longitude": -14.0233,
        "capacity": 35,
        "max_sessions_per_week": 3,
        "status": "accredited",
    },
    {
        "code": "CRG-BOKE-001",
        "name": "Centre d'Examen du Code de la Route \u2014 Bok\u00e9 1",
        "city": "Bok\u00e9",
        "commune": "Bok\u00e9-Centre",
        "prefecture": "Bok\u00e9",
        "address": "Quartier 1, Bok\u00e9",
        "latitude": 10.9333,
        "longitude": -14.2833,
        "capacity": 35,
        "max_sessions_per_week": 3,
        "status": "accredited",
    },
    {
        "code": "CRG-BOKE-002",
        "name": "Centre d'Examen du Code de la Route \u2014 Bok\u00e9 2",
        "city": "Bok\u00e9",
        "commune": "Bok\u00e9-Centre",
        "prefecture": "Bok\u00e9",
        "address": "Quartier 2, Bok\u00e9",
        "latitude": 10.9413,
        "longitude": -14.2783,
        "capacity": 35,
        "max_sessions_per_week": 3,
        "status": "accredited",
    },
    {
        "code": "CRG-BOKE-003",
        "name": "Centre d'Examen du Code de la Route \u2014 Bok\u00e9 3",
        "city": "Bok\u00e9",
        "commune": "Bok\u00e9-Centre",
        "prefecture": "Bok\u00e9",
        "address": "Quartier 3, Bok\u00e9",
        "latitude": 10.9493,
        "longitude": -14.2733,
        "capacity": 35,
        "max_sessions_per_week": 3,
        "status": "accredited",
    },
    {
        "code": "CRG-FRIA-001",
        "name": "Centre d'Examen du Code de la Route \u2014 Fria 1",
        "city": "Fria",
        "commune": "Fria-Centre",
        "prefecture": "Fria",
        "address": "Quartier 1, Fria",
        "latitude": 10.3667,
        "longitude": -13.55,
        "capacity": 35,
        "max_sessions_per_week": 3,
        "status": "accredited",
    },
    {
        "code": "CRG-FRIA-002",
        "name": "Centre d'Examen du Code de la Route \u2014 Fria 2",
        "city": "Fria",
        "commune": "Fria-Centre",
        "prefecture": "Fria",
        "address": "Quartier 2, Fria",
        "latitude": 10.3747,
        "longitude": -13.545,
        "capacity": 35,
        "max_sessions_per_week": 3,
        "status": "accredited",
    },
    {
        "code": "CRG-FRIA-003",
        "name": "Centre d'Examen du Code de la Route \u2014 Fria 3",
        "city": "Fria",
        "commune": "Fria-Centre",
        "prefecture": "Fria",
        "address": "Quartier 3, Fria",
        "latitude": 10.3827,
        "longitude": -13.54,
        "capacity": 35,
        "max_sessions_per_week": 3,
        "status": "accredited",
    },
    {
        "code": "CRG-GAOUAL-001",
        "name": "Centre d'Examen du Code de la Route \u2014 Gaoual 1",
        "city": "Gaoual",
        "commune": "Gaoual-Centre",
        "prefecture": "Gaoual",
        "address": "Quartier 1, Gaoual",
        "latitude": 11.75,
        "longitude": -13.2,
        "capacity": 35,
        "max_sessions_per_week": 3,
        "status": "accredited",
    },
    {
        "code": "CRG-GAOUAL-002",
        "name": "Centre d'Examen du Code de la Route \u2014 Gaoual 2",
        "city": "Gaoual",
        "commune": "Gaoual-Centre",
        "prefecture": "Gaoual",
        "address": "Quartier 2, Gaoual",
        "latitude": 11.758,
        "longitude": -13.195,
        "capacity": 35,
        "max_sessions_per_week": 3,
        "status": "accredited",
    },
    {
        "code": "CRG-GAOUAL-003",
        "name": "Centre d'Examen du Code de la Route \u2014 Gaoual 3",
        "city": "Gaoual",
        "commune": "Gaoual-Centre",
        "prefecture": "Gaoual",
        "address": "Quartier 3, Gaoual",
        "latitude": 11.766,
        "longitude": -13.19,
        "capacity": 35,
        "max_sessions_per_week": 3,
        "status": "accredited",
    },
    {
        "code": "CRG-COYAH-001",
        "name": "Centre d'Examen du Code de la Route \u2014 Coyah 1",
        "city": "Coyah",
        "commune": "Coyah-Centre",
        "prefecture": "Coyah",
        "address": "Quartier 1, Coyah",
        "latitude": 9.7167,
        "longitude": -13.3833,
        "capacity": 35,
        "max_sessions_per_week": 3,
        "status": "accredited",
    },
    {
        "code": "CRG-COYAH-002",
        "name": "Centre d'Examen du Code de la Route \u2014 Coyah 2",
        "city": "Coyah",
        "commune": "Coyah-Centre",
        "prefecture": "Coyah",
        "address": "Quartier 2, Coyah",
        "latitude": 9.7247,
        "longitude": -13.3783,
        "capacity": 35,
        "max_sessions_per_week": 3,
        "status": "accredited",
    },
    {
        "code": "CRG-COYAH-003",
        "name": "Centre d'Examen du Code de la Route \u2014 Coyah 3",
        "city": "Coyah",
        "commune": "Coyah-Centre",
        "prefecture": "Coyah",
        "address": "Quartier 3, Coyah",
        "latitude": 9.7327,
        "longitude": -13.3733,
        "capacity": 35,
        "max_sessions_per_week": 3,
        "status": "accredited",
    },
    {
        "code": "CRG-DUBREK-001",
        "name": "Centre d'Examen du Code de la Route \u2014 Dubr\u00e9ka 1",
        "city": "Dubr\u00e9ka",
        "commune": "Dubr\u00e9ka-Centre",
        "prefecture": "Dubr\u00e9ka",
        "address": "Quartier 1, Dubr\u00e9ka",
        "latitude": 9.7833,
        "longitude": -13.5167,
        "capacity": 35,
        "max_sessions_per_week": 3,
        "status": "accredited",
    },
    {
        "code": "CRG-DUBREK-002",
        "name": "Centre d'Examen du Code de la Route \u2014 Dubr\u00e9ka 2",
        "city": "Dubr\u00e9ka",
        "commune": "Dubr\u00e9ka-Centre",
        "prefecture": "Dubr\u00e9ka",
        "address": "Quartier 2, Dubr\u00e9ka",
        "latitude": 9.7913,
        "longitude": -13.5117,
        "capacity": 35,
        "max_sessions_per_week": 3,
        "status": "accredited",
    },
    {
        "code": "CRG-DUBREK-003",
        "name": "Centre d'Examen du Code de la Route \u2014 Dubr\u00e9ka 3",
        "city": "Dubr\u00e9ka",
        "commune": "Dubr\u00e9ka-Centre",
        "prefecture": "Dubr\u00e9ka",
        "address": "Quartier 3, Dubr\u00e9ka",
        "latitude": 9.7993,
        "longitude": -13.5067,
        "capacity": 35,
        "max_sessions_per_week": 3,
        "status": "accredited",
    },
    {
        "code": "CRG-FORECA-001",
        "name": "Centre d'Examen du Code de la Route \u2014 For\u00e9cariah 1",
        "city": "For\u00e9cariah",
        "commune": "For\u00e9cariah-Centre",
        "prefecture": "For\u00e9cariah",
        "address": "Quartier 1, For\u00e9cariah",
        "latitude": 9.4333,
        "longitude": -13.0833,
        "capacity": 35,
        "max_sessions_per_week": 3,
        "status": "accredited",
    },
    {
        "code": "CRG-FORECA-002",
        "name": "Centre d'Examen du Code de la Route \u2014 For\u00e9cariah 2",
        "city": "For\u00e9cariah",
        "commune": "For\u00e9cariah-Centre",
        "prefecture": "For\u00e9cariah",
        "address": "Quartier 2, For\u00e9cariah",
        "latitude": 9.4413,
        "longitude": -13.0783,
        "capacity": 35,
        "max_sessions_per_week": 3,
        "status": "accredited",
    },
    {
        "code": "CRG-FORECA-003",
        "name": "Centre d'Examen du Code de la Route \u2014 For\u00e9cariah 3",
        "city": "For\u00e9cariah",
        "commune": "For\u00e9cariah-Centre",
        "prefecture": "For\u00e9cariah",
        "address": "Quartier 3, For\u00e9cariah",
        "latitude": 9.4493,
        "longitude": -13.0733,
        "capacity": 35,
        "max_sessions_per_week": 3,
        "status": "accredited",
    },
    {
        "code": "CRG-KOUNDA-001",
        "name": "Centre d'Examen du Code de la Route \u2014 Koundara 1",
        "city": "Koundara",
        "commune": "Koundara-Centre",
        "prefecture": "Koundara",
        "address": "Quartier 1, Koundara",
        "latitude": 12.4833,
        "longitude": -13.3,
        "capacity": 35,
        "max_sessions_per_week": 3,
        "status": "accredited",
    },
    {
        "code": "CRG-KOUNDA-002",
        "name": "Centre d'Examen du Code de la Route \u2014 Koundara 2",
        "city": "Koundara",
        "commune": "Koundara-Centre",
        "prefecture": "Koundara",
        "address": "Quartier 2, Koundara",
        "latitude": 12.4913,
        "longitude": -13.295,
        "capacity": 35,
        "max_sessions_per_week": 3,
        "status": "accredited",
    },
    {
        "code": "CRG-KOUNDA-003",
        "name": "Centre d'Examen du Code de la Route \u2014 Koundara 3",
        "city": "Koundara",
        "commune": "Koundara-Centre",
        "prefecture": "Koundara",
        "address": "Quartier 3, Koundara",
        "latitude": 12.4993,
        "longitude": -13.29,
        "capacity": 35,
        "max_sessions_per_week": 3,
        "status": "accredited",
    },
    {
        "code": "CRG-TELIME-001",
        "name": "Centre d'Examen du Code de la Route \u2014 T\u00e9lim\u00e9l\u00e9 1",
        "city": "T\u00e9lim\u00e9l\u00e9",
        "commune": "T\u00e9lim\u00e9l\u00e9-Centre",
        "prefecture": "T\u00e9lim\u00e9l\u00e9",
        "address": "Quartier 1, T\u00e9lim\u00e9l\u00e9",
        "latitude": 10.9,
        "longitude": -13.0333,
        "capacity": 35,
        "max_sessions_per_week": 3,
        "status": "accredited",
    },
    {
        "code": "CRG-TELIME-002",
        "name": "Centre d'Examen du Code de la Route \u2014 T\u00e9lim\u00e9l\u00e9 2",
        "city": "T\u00e9lim\u00e9l\u00e9",
        "commune": "T\u00e9lim\u00e9l\u00e9-Centre",
        "prefecture": "T\u00e9lim\u00e9l\u00e9",
        "address": "Quartier 2, T\u00e9lim\u00e9l\u00e9",
        "latitude": 10.908,
        "longitude": -13.0283,
        "capacity": 35,
        "max_sessions_per_week": 3,
        "status": "accredited",
    },
    {
        "code": "CRG-TELIME-003",
        "name": "Centre d'Examen du Code de la Route \u2014 T\u00e9lim\u00e9l\u00e9 3",
        "city": "T\u00e9lim\u00e9l\u00e9",
        "commune": "T\u00e9lim\u00e9l\u00e9-Centre",
        "prefecture": "T\u00e9lim\u00e9l\u00e9",
        "address": "Quartier 3, T\u00e9lim\u00e9l\u00e9",
        "latitude": 10.916,
        "longitude": -13.0233,
        "capacity": 35,
        "max_sessions_per_week": 3,
        "status": "accredited",
    },
    {
        "code": "CRG-DALABA-001",
        "name": "Centre d'Examen du Code de la Route \u2014 Dalaba 1",
        "city": "Dalaba",
        "commune": "Dalaba-Centre",
        "prefecture": "Dalaba",
        "address": "Quartier 1, Dalaba",
        "latitude": 10.6833,
        "longitude": -12.25,
        "capacity": 35,
        "max_sessions_per_week": 3,
        "status": "accredited",
    },
    {
        "code": "CRG-DALABA-002",
        "name": "Centre d'Examen du Code de la Route \u2014 Dalaba 2",
        "city": "Dalaba",
        "commune": "Dalaba-Centre",
        "prefecture": "Dalaba",
        "address": "Quartier 2, Dalaba",
        "latitude": 10.6913,
        "longitude": -12.245,
        "capacity": 35,
        "max_sessions_per_week": 3,
        "status": "accredited",
    },
    {
        "code": "CRG-DALABA-003",
        "name": "Centre d'Examen du Code de la Route \u2014 Dalaba 3",
        "city": "Dalaba",
        "commune": "Dalaba-Centre",
        "prefecture": "Dalaba",
        "address": "Quartier 3, Dalaba",
        "latitude": 10.6993,
        "longitude": -12.24,
        "capacity": 35,
        "max_sessions_per_week": 3,
        "status": "accredited",
    },
    {
        "code": "CRG-KINDIA-001",
        "name": "Centre d'Examen du Code de la Route \u2014 Kindia 1",
        "city": "Kindia",
        "commune": "Kindia-Centre",
        "prefecture": "Kindia",
        "address": "Quartier 1, Kindia",
        "latitude": 10.0667,
        "longitude": -12.8667,
        "capacity": 35,
        "max_sessions_per_week": 3,
        "status": "accredited",
    },
    {
        "code": "CRG-KINDIA-002",
        "name": "Centre d'Examen du Code de la Route \u2014 Kindia 2",
        "city": "Kindia",
        "commune": "Kindia-Centre",
        "prefecture": "Kindia",
        "address": "Quartier 2, Kindia",
        "latitude": 10.0747,
        "longitude": -12.8617,
        "capacity": 35,
        "max_sessions_per_week": 3,
        "status": "accredited",
    },
    {
        "code": "CRG-KINDIA-003",
        "name": "Centre d'Examen du Code de la Route \u2014 Kindia 3",
        "city": "Kindia",
        "commune": "Kindia-Centre",
        "prefecture": "Kindia",
        "address": "Quartier 3, Kindia",
        "latitude": 10.0827,
        "longitude": -12.8567,
        "capacity": 35,
        "max_sessions_per_week": 3,
        "status": "accredited",
    },
    {
        "code": "CRG-LABE-001",
        "name": "Centre d'Examen du Code de la Route \u2014 Lab\u00e9 1",
        "city": "Lab\u00e9",
        "commune": "Lab\u00e9-Centre",
        "prefecture": "Lab\u00e9",
        "address": "Quartier 1, Lab\u00e9",
        "latitude": 11.3167,
        "longitude": -12.2833,
        "capacity": 35,
        "max_sessions_per_week": 3,
        "status": "accredited",
    },
    {
        "code": "CRG-LABE-002",
        "name": "Centre d'Examen du Code de la Route \u2014 Lab\u00e9 2",
        "city": "Lab\u00e9",
        "commune": "Lab\u00e9-Centre",
        "prefecture": "Lab\u00e9",
        "address": "Quartier 2, Lab\u00e9",
        "latitude": 11.3247,
        "longitude": -12.2783,
        "capacity": 35,
        "max_sessions_per_week": 3,
        "status": "accredited",
    },
    {
        "code": "CRG-LABE-003",
        "name": "Centre d'Examen du Code de la Route \u2014 Lab\u00e9 3",
        "city": "Lab\u00e9",
        "commune": "Lab\u00e9-Centre",
        "prefecture": "Lab\u00e9",
        "address": "Quartier 3, Lab\u00e9",
        "latitude": 11.3327,
        "longitude": -12.2733,
        "capacity": 35,
        "max_sessions_per_week": 3,
        "status": "accredited",
    },
    {
        "code": "CRG-LELOUM-001",
        "name": "Centre d'Examen du Code de la Route \u2014 L\u00e9louma 1",
        "city": "L\u00e9louma",
        "commune": "L\u00e9louma-Centre",
        "prefecture": "L\u00e9louma",
        "address": "Quartier 1, L\u00e9louma",
        "latitude": 11.25,
        "longitude": -12.6833,
        "capacity": 35,
        "max_sessions_per_week": 3,
        "status": "accredited",
    },
    {
        "code": "CRG-LELOUM-002",
        "name": "Centre d'Examen du Code de la Route \u2014 L\u00e9louma 2",
        "city": "L\u00e9louma",
        "commune": "L\u00e9louma-Centre",
        "prefecture": "L\u00e9louma",
        "address": "Quartier 2, L\u00e9louma",
        "latitude": 11.258,
        "longitude": -12.6783,
        "capacity": 35,
        "max_sessions_per_week": 3,
        "status": "accredited",
    },
    {
        "code": "CRG-LELOUM-003",
        "name": "Centre d'Examen du Code de la Route \u2014 L\u00e9louma 3",
        "city": "L\u00e9louma",
        "commune": "L\u00e9louma-Centre",
        "prefecture": "L\u00e9louma",
        "address": "Quartier 3, L\u00e9louma",
        "latitude": 11.266,
        "longitude": -12.6733,
        "capacity": 35,
        "max_sessions_per_week": 3,
        "status": "accredited",
    },
    {
        "code": "CRG-MALI-001",
        "name": "Centre d'Examen du Code de la Route \u2014 Mali 1",
        "city": "Mali",
        "commune": "Mali-Centre",
        "prefecture": "Mali",
        "address": "Quartier 1, Mali",
        "latitude": 12.0833,
        "longitude": -12.3,
        "capacity": 35,
        "max_sessions_per_week": 3,
        "status": "accredited",
    },
    {
        "code": "CRG-MALI-002",
        "name": "Centre d'Examen du Code de la Route \u2014 Mali 2",
        "city": "Mali",
        "commune": "Mali-Centre",
        "prefecture": "Mali",
        "address": "Quartier 2, Mali",
        "latitude": 12.0913,
        "longitude": -12.295,
        "capacity": 35,
        "max_sessions_per_week": 3,
        "status": "accredited",
    },
    {
        "code": "CRG-MALI-003",
        "name": "Centre d'Examen du Code de la Route \u2014 Mali 3",
        "city": "Mali",
        "commune": "Mali-Centre",
        "prefecture": "Mali",
        "address": "Quartier 3, Mali",
        "latitude": 12.0993,
        "longitude": -12.29,
        "capacity": 35,
        "max_sessions_per_week": 3,
        "status": "accredited",
    },
    {
        "code": "CRG-MAMOU-001",
        "name": "Centre d'Examen du Code de la Route \u2014 Mamou 1",
        "city": "Mamou",
        "commune": "Mamou-Centre",
        "prefecture": "Mamou",
        "address": "Quartier 1, Mamou",
        "latitude": 10.3667,
        "longitude": -12.0833,
        "capacity": 35,
        "max_sessions_per_week": 3,
        "status": "accredited",
    },
    {
        "code": "CRG-MAMOU-002",
        "name": "Centre d'Examen du Code de la Route \u2014 Mamou 2",
        "city": "Mamou",
        "commune": "Mamou-Centre",
        "prefecture": "Mamou",
        "address": "Quartier 2, Mamou",
        "latitude": 10.3747,
        "longitude": -12.0783,
        "capacity": 35,
        "max_sessions_per_week": 3,
        "status": "accredited",
    },
    {
        "code": "CRG-MAMOU-003",
        "name": "Centre d'Examen du Code de la Route \u2014 Mamou 3",
        "city": "Mamou",
        "commune": "Mamou-Centre",
        "prefecture": "Mamou",
        "address": "Quartier 3, Mamou",
        "latitude": 10.3827,
        "longitude": -12.0733,
        "capacity": 35,
        "max_sessions_per_week": 3,
        "status": "accredited",
    },
    {
        "code": "CRG-PITA-001",
        "name": "Centre d'Examen du Code de la Route \u2014 Pita 1",
        "city": "Pita",
        "commune": "Pita-Centre",
        "prefecture": "Pita",
        "address": "Quartier 1, Pita",
        "latitude": 11.0667,
        "longitude": -12.4,
        "capacity": 35,
        "max_sessions_per_week": 3,
        "status": "accredited",
    },
    {
        "code": "CRG-PITA-002",
        "name": "Centre d'Examen du Code de la Route \u2014 Pita 2",
        "city": "Pita",
        "commune": "Pita-Centre",
        "prefecture": "Pita",
        "address": "Quartier 2, Pita",
        "latitude": 11.0747,
        "longitude": -12.395,
        "capacity": 35,
        "max_sessions_per_week": 3,
        "status": "accredited",
    },
    {
        "code": "CRG-PITA-003",
        "name": "Centre d'Examen du Code de la Route \u2014 Pita 3",
        "city": "Pita",
        "commune": "Pita-Centre",
        "prefecture": "Pita",
        "address": "Quartier 3, Pita",
        "latitude": 11.0827,
        "longitude": -12.39,
        "capacity": 35,
        "max_sessions_per_week": 3,
        "status": "accredited",
    },
    {
        "code": "CRG-TOUGUE-001",
        "name": "Centre d'Examen du Code de la Route \u2014 Tougu\u00e9 1",
        "city": "Tougu\u00e9",
        "commune": "Tougu\u00e9-Centre",
        "prefecture": "Tougu\u00e9",
        "address": "Quartier 1, Tougu\u00e9",
        "latitude": 11.4333,
        "longitude": -11.6833,
        "capacity": 35,
        "max_sessions_per_week": 3,
        "status": "accredited",
    },
    {
        "code": "CRG-TOUGUE-002",
        "name": "Centre d'Examen du Code de la Route \u2014 Tougu\u00e9 2",
        "city": "Tougu\u00e9",
        "commune": "Tougu\u00e9-Centre",
        "prefecture": "Tougu\u00e9",
        "address": "Quartier 2, Tougu\u00e9",
        "latitude": 11.4413,
        "longitude": -11.6783,
        "capacity": 35,
        "max_sessions_per_week": 3,
        "status": "accredited",
    },
    {
        "code": "CRG-TOUGUE-003",
        "name": "Centre d'Examen du Code de la Route \u2014 Tougu\u00e9 3",
        "city": "Tougu\u00e9",
        "commune": "Tougu\u00e9-Centre",
        "prefecture": "Tougu\u00e9",
        "address": "Quartier 3, Tougu\u00e9",
        "latitude": 11.4493,
        "longitude": -11.6733,
        "capacity": 35,
        "max_sessions_per_week": 3,
        "status": "accredited",
    },
    {
        "code": "CRG-DABOLA-001",
        "name": "Centre d'Examen du Code de la Route \u2014 Dabola 1",
        "city": "Dabola",
        "commune": "Dabola-Centre",
        "prefecture": "Dabola",
        "address": "Quartier 1, Dabola",
        "latitude": 10.75,
        "longitude": -11.1167,
        "capacity": 35,
        "max_sessions_per_week": 3,
        "status": "accredited",
    },
    {
        "code": "CRG-DABOLA-002",
        "name": "Centre d'Examen du Code de la Route \u2014 Dabola 2",
        "city": "Dabola",
        "commune": "Dabola-Centre",
        "prefecture": "Dabola",
        "address": "Quartier 2, Dabola",
        "latitude": 10.758,
        "longitude": -11.1117,
        "capacity": 35,
        "max_sessions_per_week": 3,
        "status": "accredited",
    },
    {
        "code": "CRG-DABOLA-003",
        "name": "Centre d'Examen du Code de la Route \u2014 Dabola 3",
        "city": "Dabola",
        "commune": "Dabola-Centre",
        "prefecture": "Dabola",
        "address": "Quartier 3, Dabola",
        "latitude": 10.766,
        "longitude": -11.1067,
        "capacity": 35,
        "max_sessions_per_week": 3,
        "status": "accredited",
    },
    {
        "code": "CRG-DINGUI-001",
        "name": "Centre d'Examen du Code de la Route \u2014 Dinguiraye 1",
        "city": "Dinguiraye",
        "commune": "Dinguiraye-Centre",
        "prefecture": "Dinguiraye",
        "address": "Quartier 1, Dinguiraye",
        "latitude": 11.3,
        "longitude": -10.7167,
        "capacity": 35,
        "max_sessions_per_week": 3,
        "status": "accredited",
    },
    {
        "code": "CRG-DINGUI-002",
        "name": "Centre d'Examen du Code de la Route \u2014 Dinguiraye 2",
        "city": "Dinguiraye",
        "commune": "Dinguiraye-Centre",
        "prefecture": "Dinguiraye",
        "address": "Quartier 2, Dinguiraye",
        "latitude": 11.308,
        "longitude": -10.7117,
        "capacity": 35,
        "max_sessions_per_week": 3,
        "status": "accredited",
    },
    {
        "code": "CRG-DINGUI-003",
        "name": "Centre d'Examen du Code de la Route \u2014 Dinguiraye 3",
        "city": "Dinguiraye",
        "commune": "Dinguiraye-Centre",
        "prefecture": "Dinguiraye",
        "address": "Quartier 3, Dinguiraye",
        "latitude": 11.316,
        "longitude": -10.7067,
        "capacity": 35,
        "max_sessions_per_week": 3,
        "status": "accredited",
    },
    {
        "code": "CRG-FARANA-001",
        "name": "Centre d'Examen du Code de la Route \u2014 Faranah 1",
        "city": "Faranah",
        "commune": "Faranah-Centre",
        "prefecture": "Faranah",
        "address": "Quartier 1, Faranah",
        "latitude": 10.0333,
        "longitude": -10.75,
        "capacity": 35,
        "max_sessions_per_week": 3,
        "status": "accredited",
    },
    {
        "code": "CRG-FARANA-002",
        "name": "Centre d'Examen du Code de la Route \u2014 Faranah 2",
        "city": "Faranah",
        "commune": "Faranah-Centre",
        "prefecture": "Faranah",
        "address": "Quartier 2, Faranah",
        "latitude": 10.0413,
        "longitude": -10.745,
        "capacity": 35,
        "max_sessions_per_week": 3,
        "status": "accredited",
    },
    {
        "code": "CRG-FARANA-003",
        "name": "Centre d'Examen du Code de la Route \u2014 Faranah 3",
        "city": "Faranah",
        "commune": "Faranah-Centre",
        "prefecture": "Faranah",
        "address": "Quartier 3, Faranah",
        "latitude": 10.0493,
        "longitude": -10.74,
        "capacity": 35,
        "max_sessions_per_week": 3,
        "status": "accredited",
    },
    {
        "code": "CRG-KANKAN-001",
        "name": "Centre d'Examen du Code de la Route \u2014 Kankan 1",
        "city": "Kankan",
        "commune": "Kankan-Centre",
        "prefecture": "Kankan",
        "address": "Quartier 1, Kankan",
        "latitude": 10.3833,
        "longitude": -9.2833,
        "capacity": 35,
        "max_sessions_per_week": 3,
        "status": "accredited",
    },
    {
        "code": "CRG-KANKAN-002",
        "name": "Centre d'Examen du Code de la Route \u2014 Kankan 2",
        "city": "Kankan",
        "commune": "Kankan-Centre",
        "prefecture": "Kankan",
        "address": "Quartier 2, Kankan",
        "latitude": 10.3913,
        "longitude": -9.2783,
        "capacity": 35,
        "max_sessions_per_week": 3,
        "status": "accredited",
    },
    {
        "code": "CRG-KANKAN-003",
        "name": "Centre d'Examen du Code de la Route \u2014 Kankan 3",
        "city": "Kankan",
        "commune": "Kankan-Centre",
        "prefecture": "Kankan",
        "address": "Quartier 3, Kankan",
        "latitude": 10.3993,
        "longitude": -9.2733,
        "capacity": 35,
        "max_sessions_per_week": 3,
        "status": "accredited",
    },
    {
        "code": "CRG-KEROUA-001",
        "name": "Centre d'Examen du Code de la Route \u2014 K\u00e9rouan\u00e9 1",
        "city": "K\u00e9rouan\u00e9",
        "commune": "K\u00e9rouan\u00e9-Centre",
        "prefecture": "K\u00e9rouan\u00e9",
        "address": "Quartier 1, K\u00e9rouan\u00e9",
        "latitude": 9.2667,
        "longitude": -9.0167,
        "capacity": 35,
        "max_sessions_per_week": 3,
        "status": "accredited",
    },
    {
        "code": "CRG-KEROUA-002",
        "name": "Centre d'Examen du Code de la Route \u2014 K\u00e9rouan\u00e9 2",
        "city": "K\u00e9rouan\u00e9",
        "commune": "K\u00e9rouan\u00e9-Centre",
        "prefecture": "K\u00e9rouan\u00e9",
        "address": "Quartier 2, K\u00e9rouan\u00e9",
        "latitude": 9.2747,
        "longitude": -9.0117,
        "capacity": 35,
        "max_sessions_per_week": 3,
        "status": "accredited",
    },
    {
        "code": "CRG-KEROUA-003",
        "name": "Centre d'Examen du Code de la Route \u2014 K\u00e9rouan\u00e9 3",
        "city": "K\u00e9rouan\u00e9",
        "commune": "K\u00e9rouan\u00e9-Centre",
        "prefecture": "K\u00e9rouan\u00e9",
        "address": "Quartier 3, K\u00e9rouan\u00e9",
        "latitude": 9.2827,
        "longitude": -9.0067,
        "capacity": 35,
        "max_sessions_per_week": 3,
        "status": "accredited",
    },
    {
        "code": "CRG-KOUROU-001",
        "name": "Centre d'Examen du Code de la Route \u2014 Kouroussa 1",
        "city": "Kouroussa",
        "commune": "Kouroussa-Centre",
        "prefecture": "Kouroussa",
        "address": "Quartier 1, Kouroussa",
        "latitude": 10.65,
        "longitude": -9.8833,
        "capacity": 35,
        "max_sessions_per_week": 3,
        "status": "accredited",
    },
    {
        "code": "CRG-KOUROU-002",
        "name": "Centre d'Examen du Code de la Route \u2014 Kouroussa 2",
        "city": "Kouroussa",
        "commune": "Kouroussa-Centre",
        "prefecture": "Kouroussa",
        "address": "Quartier 2, Kouroussa",
        "latitude": 10.658,
        "longitude": -9.8783,
        "capacity": 35,
        "max_sessions_per_week": 3,
        "status": "accredited",
    },
    {
        "code": "CRG-KOUROU-003",
        "name": "Centre d'Examen du Code de la Route \u2014 Kouroussa 3",
        "city": "Kouroussa",
        "commune": "Kouroussa-Centre",
        "prefecture": "Kouroussa",
        "address": "Quartier 3, Kouroussa",
        "latitude": 10.666,
        "longitude": -9.8733,
        "capacity": 35,
        "max_sessions_per_week": 3,
        "status": "accredited",
    },
    {
        "code": "CRG-MANDIA-001",
        "name": "Centre d'Examen du Code de la Route \u2014 Mandiana 1",
        "city": "Mandiana",
        "commune": "Mandiana-Centre",
        "prefecture": "Mandiana",
        "address": "Quartier 1, Mandiana",
        "latitude": 10.6167,
        "longitude": -8.6833,
        "capacity": 35,
        "max_sessions_per_week": 3,
        "status": "accredited",
    },
    {
        "code": "CRG-MANDIA-002",
        "name": "Centre d'Examen du Code de la Route \u2014 Mandiana 2",
        "city": "Mandiana",
        "commune": "Mandiana-Centre",
        "prefecture": "Mandiana",
        "address": "Quartier 2, Mandiana",
        "latitude": 10.6247,
        "longitude": -8.6783,
        "capacity": 35,
        "max_sessions_per_week": 3,
        "status": "accredited",
    },
    {
        "code": "CRG-MANDIA-003",
        "name": "Centre d'Examen du Code de la Route \u2014 Mandiana 3",
        "city": "Mandiana",
        "commune": "Mandiana-Centre",
        "prefecture": "Mandiana",
        "address": "Quartier 3, Mandiana",
        "latitude": 10.6327,
        "longitude": -8.6733,
        "capacity": 35,
        "max_sessions_per_week": 3,
        "status": "accredited",
    },
    {
        "code": "CRG-SIGUIR-001",
        "name": "Centre d'Examen du Code de la Route \u2014 Siguiri 1",
        "city": "Siguiri",
        "commune": "Siguiri-Centre",
        "prefecture": "Siguiri",
        "address": "Quartier 1, Siguiri",
        "latitude": 11.4167,
        "longitude": -9.1667,
        "capacity": 35,
        "max_sessions_per_week": 3,
        "status": "accredited",
    },
    {
        "code": "CRG-SIGUIR-002",
        "name": "Centre d'Examen du Code de la Route \u2014 Siguiri 2",
        "city": "Siguiri",
        "commune": "Siguiri-Centre",
        "prefecture": "Siguiri",
        "address": "Quartier 2, Siguiri",
        "latitude": 11.4247,
        "longitude": -9.1617,
        "capacity": 35,
        "max_sessions_per_week": 3,
        "status": "accredited",
    },
    {
        "code": "CRG-SIGUIR-003",
        "name": "Centre d'Examen du Code de la Route \u2014 Siguiri 3",
        "city": "Siguiri",
        "commune": "Siguiri-Centre",
        "prefecture": "Siguiri",
        "address": "Quartier 3, Siguiri",
        "latitude": 11.4327,
        "longitude": -9.1567,
        "capacity": 35,
        "max_sessions_per_week": 3,
        "status": "accredited",
    },
    {
        "code": "CRG-BEYLA-001",
        "name": "Centre d'Examen du Code de la Route \u2014 Beyla 1",
        "city": "Beyla",
        "commune": "Beyla-Centre",
        "prefecture": "Beyla",
        "address": "Quartier 1, Beyla",
        "latitude": 8.6833,
        "longitude": -8.65,
        "capacity": 35,
        "max_sessions_per_week": 3,
        "status": "accredited",
    },
    {
        "code": "CRG-BEYLA-002",
        "name": "Centre d'Examen du Code de la Route \u2014 Beyla 2",
        "city": "Beyla",
        "commune": "Beyla-Centre",
        "prefecture": "Beyla",
        "address": "Quartier 2, Beyla",
        "latitude": 8.6913,
        "longitude": -8.645,
        "capacity": 35,
        "max_sessions_per_week": 3,
        "status": "accredited",
    },
    {
        "code": "CRG-BEYLA-003",
        "name": "Centre d'Examen du Code de la Route \u2014 Beyla 3",
        "city": "Beyla",
        "commune": "Beyla-Centre",
        "prefecture": "Beyla",
        "address": "Quartier 3, Beyla",
        "latitude": 8.6993,
        "longitude": -8.64,
        "capacity": 35,
        "max_sessions_per_week": 3,
        "status": "accredited",
    },
    {
        "code": "CRG-GUECKE-001",
        "name": "Centre d'Examen du Code de la Route \u2014 Gu\u00e9ck\u00e9dou 1",
        "city": "Gu\u00e9ck\u00e9dou",
        "commune": "Gu\u00e9ck\u00e9dou-Centre",
        "prefecture": "Gu\u00e9ck\u00e9dou",
        "address": "Quartier 1, Gu\u00e9ck\u00e9dou",
        "latitude": 8.55,
        "longitude": -10.1333,
        "capacity": 35,
        "max_sessions_per_week": 3,
        "status": "accredited",
    },
    {
        "code": "CRG-GUECKE-002",
        "name": "Centre d'Examen du Code de la Route \u2014 Gu\u00e9ck\u00e9dou 2",
        "city": "Gu\u00e9ck\u00e9dou",
        "commune": "Gu\u00e9ck\u00e9dou-Centre",
        "prefecture": "Gu\u00e9ck\u00e9dou",
        "address": "Quartier 2, Gu\u00e9ck\u00e9dou",
        "latitude": 8.558,
        "longitude": -10.1283,
        "capacity": 35,
        "max_sessions_per_week": 3,
        "status": "accredited",
    },
    {
        "code": "CRG-GUECKE-003",
        "name": "Centre d'Examen du Code de la Route \u2014 Gu\u00e9ck\u00e9dou 3",
        "city": "Gu\u00e9ck\u00e9dou",
        "commune": "Gu\u00e9ck\u00e9dou-Centre",
        "prefecture": "Gu\u00e9ck\u00e9dou",
        "address": "Quartier 3, Gu\u00e9ck\u00e9dou",
        "latitude": 8.566,
        "longitude": -10.1233,
        "capacity": 35,
        "max_sessions_per_week": 3,
        "status": "accredited",
    },
    {
        "code": "CRG-KISSID-001",
        "name": "Centre d'Examen du Code de la Route \u2014 Kissidougou 1",
        "city": "Kissidougou",
        "commune": "Kissidougou-Centre",
        "prefecture": "Kissidougou",
        "address": "Quartier 1, Kissidougou",
        "latitude": 9.1833,
        "longitude": -10.1,
        "capacity": 35,
        "max_sessions_per_week": 3,
        "status": "accredited",
    },
    {
        "code": "CRG-KISSID-002",
        "name": "Centre d'Examen du Code de la Route \u2014 Kissidougou 2",
        "city": "Kissidougou",
        "commune": "Kissidougou-Centre",
        "prefecture": "Kissidougou",
        "address": "Quartier 2, Kissidougou",
        "latitude": 9.1913,
        "longitude": -10.095,
        "capacity": 35,
        "max_sessions_per_week": 3,
        "status": "accredited",
    },
    {
        "code": "CRG-KISSID-003",
        "name": "Centre d'Examen du Code de la Route \u2014 Kissidougou 3",
        "city": "Kissidougou",
        "commune": "Kissidougou-Centre",
        "prefecture": "Kissidougou",
        "address": "Quartier 3, Kissidougou",
        "latitude": 9.1993,
        "longitude": -10.09,
        "capacity": 35,
        "max_sessions_per_week": 3,
        "status": "accredited",
    },
    {
        "code": "CRG-LOLA-001",
        "name": "Centre d'Examen du Code de la Route \u2014 Lola 1",
        "city": "Lola",
        "commune": "Lola-Centre",
        "prefecture": "Lola",
        "address": "Quartier 1, Lola",
        "latitude": 7.8167,
        "longitude": -8.5333,
        "capacity": 35,
        "max_sessions_per_week": 3,
        "status": "accredited",
    },
    {
        "code": "CRG-LOLA-002",
        "name": "Centre d'Examen du Code de la Route \u2014 Lola 2",
        "city": "Lola",
        "commune": "Lola-Centre",
        "prefecture": "Lola",
        "address": "Quartier 2, Lola",
        "latitude": 7.8247,
        "longitude": -8.5283,
        "capacity": 35,
        "max_sessions_per_week": 3,
        "status": "accredited",
    },
    {
        "code": "CRG-LOLA-003",
        "name": "Centre d'Examen du Code de la Route \u2014 Lola 3",
        "city": "Lola",
        "commune": "Lola-Centre",
        "prefecture": "Lola",
        "address": "Quartier 3, Lola",
        "latitude": 7.8327,
        "longitude": -8.5233,
        "capacity": 35,
        "max_sessions_per_week": 3,
        "status": "accredited",
    },
    {
        "code": "CRG-MACENT-001",
        "name": "Centre d'Examen du Code de la Route \u2014 Macenta 1",
        "city": "Macenta",
        "commune": "Macenta-Centre",
        "prefecture": "Macenta",
        "address": "Quartier 1, Macenta",
        "latitude": 8.55,
        "longitude": -9.4667,
        "capacity": 35,
        "max_sessions_per_week": 3,
        "status": "accredited",
    },
    {
        "code": "CRG-MACENT-002",
        "name": "Centre d'Examen du Code de la Route \u2014 Macenta 2",
        "city": "Macenta",
        "commune": "Macenta-Centre",
        "prefecture": "Macenta",
        "address": "Quartier 2, Macenta",
        "latitude": 8.558,
        "longitude": -9.4617,
        "capacity": 35,
        "max_sessions_per_week": 3,
        "status": "accredited",
    },
    {
        "code": "CRG-MACENT-003",
        "name": "Centre d'Examen du Code de la Route \u2014 Macenta 3",
        "city": "Macenta",
        "commune": "Macenta-Centre",
        "prefecture": "Macenta",
        "address": "Quartier 3, Macenta",
        "latitude": 8.566,
        "longitude": -9.4567,
        "capacity": 35,
        "max_sessions_per_week": 3,
        "status": "accredited",
    },
    {
        "code": "CRG-NZEREK-001",
        "name": "Centre d'Examen du Code de la Route \u2014 N'Z\u00e9r\u00e9kor\u00e9 1",
        "city": "N'Z\u00e9r\u00e9kor\u00e9",
        "commune": "N'Z\u00e9r\u00e9kor\u00e9-Centre",
        "prefecture": "N'Z\u00e9r\u00e9kor\u00e9",
        "address": "Quartier 1, N'Z\u00e9r\u00e9kor\u00e9",
        "latitude": 7.75,
        "longitude": -8.8167,
        "capacity": 35,
        "max_sessions_per_week": 3,
        "status": "accredited",
    },
    {
        "code": "CRG-NZEREK-002",
        "name": "Centre d'Examen du Code de la Route \u2014 N'Z\u00e9r\u00e9kor\u00e9 2",
        "city": "N'Z\u00e9r\u00e9kor\u00e9",
        "commune": "N'Z\u00e9r\u00e9kor\u00e9-Centre",
        "prefecture": "N'Z\u00e9r\u00e9kor\u00e9",
        "address": "Quartier 2, N'Z\u00e9r\u00e9kor\u00e9",
        "latitude": 7.758,
        "longitude": -8.8117,
        "capacity": 35,
        "max_sessions_per_week": 3,
        "status": "accredited",
    },
    {
        "code": "CRG-NZEREK-003",
        "name": "Centre d'Examen du Code de la Route \u2014 N'Z\u00e9r\u00e9kor\u00e9 3",
        "city": "N'Z\u00e9r\u00e9kor\u00e9",
        "commune": "N'Z\u00e9r\u00e9kor\u00e9-Centre",
        "prefecture": "N'Z\u00e9r\u00e9kor\u00e9",
        "address": "Quartier 3, N'Z\u00e9r\u00e9kor\u00e9",
        "latitude": 7.766,
        "longitude": -8.8067,
        "capacity": 35,
        "max_sessions_per_week": 3,
        "status": "accredited",
    },
    {
        "code": "CRG-YOMOU-001",
        "name": "Centre d'Examen du Code de la Route \u2014 Yomou 1",
        "city": "Yomou",
        "commune": "Yomou-Centre",
        "prefecture": "Yomou",
        "address": "Quartier 1, Yomou",
        "latitude": 7.5667,
        "longitude": -9.25,
        "capacity": 35,
        "max_sessions_per_week": 3,
        "status": "accredited",
    },
    {
        "code": "CRG-YOMOU-002",
        "name": "Centre d'Examen du Code de la Route \u2014 Yomou 2",
        "city": "Yomou",
        "commune": "Yomou-Centre",
        "prefecture": "Yomou",
        "address": "Quartier 2, Yomou",
        "latitude": 7.5747,
        "longitude": -9.245,
        "capacity": 35,
        "max_sessions_per_week": 3,
        "status": "accredited",
    },
    {
        "code": "CRG-YOMOU-003",
        "name": "Centre d'Examen du Code de la Route \u2014 Yomou 3",
        "city": "Yomou",
        "commune": "Yomou-Centre",
        "prefecture": "Yomou",
        "address": "Quartier 3, Yomou",
        "latitude": 7.5827,
        "longitude": -9.24,
        "capacity": 35,
        "max_sessions_per_week": 3,
        "status": "accredited",
    },
]



def seed_centers(db) -> dict[str, Center]:
    centers = {}
    for c in CENTERS:
        existing = db.scalar(select(Center).where(Center.code == c["code"]))
        if existing:
            # Mettre à jour les nouvelles colonnes géographiques et règles métier
            for field in ["commune", "prefecture", "latitude", "longitude", "capacity", "max_sessions_per_week"]:
                if field in c and getattr(existing, field, None) is None:
                    setattr(existing, field, c[field])
            centers[c["code"]] = existing
            continue
        center = Center(**c)
        db.add(center)
        db.flush()
        centers[c["code"]] = center
    db.commit()
    conakry = sum(1 for c in CENTERS if c.get("city") == "Conakry")
    prefectures = len(centers) - conakry
    print(f"  ✅ {len(centers)} centres ({conakry} Conakry + {prefectures} préfectures)")
    return centers


# ── QUESTIONS ─────────────────────────────────────────────────────────────



def _stable_hash(text: str) -> int:
    """Hash déterministe (hash() Python est randomisé entre process)."""
    import hashlib
    return int(hashlib.md5(text.encode()).hexdigest(), 16)


def _get_media_for_question(text: str, category: str) -> tuple[str | None, str | None, str | None]:
    """
    Retourne (media_type, media_url, media_alt) selon le texte et la catégorie.
    Mapping précis vers les panneaux français normalisés et les scènes de conduite.
    Objectif : que le visuel corresponde vraiment à la question (comme les
    apps FR : Codes Rousseau, Ornikar, ENPC).
    """
    t = text.lower()

    # ═══ FEUX TRICOLORES ═══════════════════════════════════════════════════
    if "rouge et orange" in t or "rouge fixe et orange" in t:
        return "scene", "traffic_light_red_orange", "Feu rouge et orange simultanés"
    if "feu orange" in t or "passe à l'orange" in t or "orange clignotant" in t or "orange fixe" in t:
        return "scene", "traffic_light_orange", "Feu tricolore orange"
    if "feu vert" in t:
        return "scene", "traffic_light_red", "Feu tricolore"
    if "feu rouge" in t or "feu tricolore" in t or "feu est rouge" in t or "passage à niveau" in t:
        return "scene", "traffic_light_red", "Feu tricolore — arrêt obligatoire"

    # ═══ PANNEAUX D'INTERDICTION (rond rouge) ═════════════════════════════
    if "sens interdit" in t or "barre horizontale blanche" in t:
        return "sign", "no_entry", "Panneau Sens interdit"
    if ("dépasser" in t or "dépassement" in t) and ("interdit" in t or "panneau" in t):
        return "sign", "no_overtaking", "Interdiction de dépasser"
    if ("tourner à gauche" in t or "à gauche" in t) and "interdit" in t:
        return "sign", "no_left_turn", "Interdiction de tourner à gauche"
    if ("arrêt" in t and "stationnement" in t and "interdit" in t) or "arrêt interdit" in t:
        return "sign", "no_stopping", "Arrêt et stationnement interdits"
    if "stationnement interdit" in t or ("stationnement" in t and "interdit" in t):
        return "sign", "no_parking", "Stationnement interdit"

    # ═══ VITESSES (rond rouge, chiffre) ═══════════════════════════════════
    if "130" in t:
        return "sign", "speed_130", "Limitation 130 km/h (autoroute)"
    if "110" in t:
        return "sign", "speed_110", "Limitation 110 km/h"
    if "100" in t:
        return "sign", "speed_100", "Limitation 100 km/h"
    if "90" in t:
        return "sign", "speed_90", "Limitation 90 km/h"
    if "70" in t:
        return "sign", "speed_70", "Limitation 70 km/h"
    if "zone 30" in t or ("30" in t and ("zone" in t or "résidentielle" in t)):
        return "sign", "speed_30", "Zone 30"
    if "50" in t and ("agglomération" in t or "ville" in t or "entrée" in t or "km/h" in t):
        return "sign", "speed_50", "Limitation 50 km/h"

    # ═══ PANNEAUX DE PRIORITÉ ═════════════════════════════════════════════
    if "stop" in t or "marquage 'stop'" in t:
        return "sign", "stop", "Panneau STOP — arrêt obligatoire"
    if "cédez le passage" in t or "céder le passage" in t or "triangle inversé" in t or "triangle pointe en bas" in t:
        return "sign", "give_way", "Cédez le passage"
    if "route prioritaire" in t or ("priorité" in t and ("losange" in t or "carré jaune" in t)):
        return "sign", "priority", "Route prioritaire"

    # ═══ PANNEAUX D'OBLIGATION (rond bleu) ════════════════════════════════
    if "rond bleu" in t or ("bleu" in t and "flèche" in t) or "tout droit obligatoire" in t or "direction obligatoire tout droit" in t:
        return "sign", "mandatory_straight", "Direction obligatoire"
    if "giratoire" in t or "rond-point" in t or "sens giratoire" in t:
        return "sign", "roundabout", "Carrefour à sens giratoire"
    if "obligation" in t and "droite" in t:
        return "sign", "mandatory_right", "Obligation de tourner à droite"

    # ═══ MARQUAGES AU SOL ═════════════════════════════════════════════════
    if "ligne blanche continue" in t or "ligne continue" in t:
        return "sign", "no_overtaking", "Ligne continue — franchissement interdit"

    # ═══ PANNEAUX DE DANGER (triangle rouge) ══════════════════════════════
    if "passage piéton" in t or "passage protégé" in t or "passage clouté" in t or ("piéton" in t and "traverse" in t):
        return "sign", "pedestrian_crossing", "Passage pour piétons"
    if "enfant" in t or "école" in t or "zone scolaire" in t or "sortie d'école" in t:
        return "sign", "danger_children", "Passage d'enfants"
    if "chaussée glissante" in t or "verglas" in t or "route glissante" in t or ("glissant" in t):
        return "sign", "danger_slippery", "Chaussée glissante"
    if "virage" in t or "courbe dangereuse" in t:
        return "sign", "danger_bend", "Virage dangereux"
    if "carrefour" in t and "giratoire" in t:
        return "sign", "danger_roundabout", "Carrefour à sens giratoire (annonce)"
    if "autres dangers" in t or "danger non défini" in t or ("panneau" in t and "danger" in t and "triangle" in t):
        return "sign", "danger_generic", "Autres dangers"

    # ═══ FIN DE PRESCRIPTION ══════════════════════════════════════════════
    if "fin de" in t and ("limitation" in t or "interdiction" in t or "toutes" in t):
        return "sign", "end_restriction", "Fin de toutes interdictions"
    if "parking" in t or ("stationnement" in t and "autorisé" in t):
        return "sign", "parking", "Stationnement autorisé"

    # ═══ SCÈNES DE CONDUITE (vue subjective) ══════════════════════════════
    if ("priorité" in t and "droite" in t) or ("intersection" in t and ("sans panneau" in t or "sans signalisation" in t)):
        return "scene", "intersection_priority_right", "Intersection — priorité à droite"
    if "ambulance" in t or "gyrophare" in t or "véhicule prioritaire" in t or "samu" in t or "pompier" in t or "convoi" in t or ("sirène" in t):
        return "scene", "situation_emergency_vehicle", "Véhicule d'urgence prioritaire"
    if "distance de sécurité" in t or "2 secondes" in t or "intervalle" in t or ("freinage" in t and "distance" in t):
        return "scene", "situation_safe_distance", "Distance de sécurité"
    if "nuit" in t or "nocturne" in t or ("phare" in t and ("éclaire" in t or "croisement" in t or "route" in t)) or "feux de route" in t:
        return "scene", "night_driving", "Conduite de nuit"
    if "pluie" in t or "mouillée" in t or "brouillard" in t or "inondation" in t or ("visibilité" in t and ("réduite" in t or "50" in t)):
        return "scene", "rain_driving", "Conditions météo dégradées"
    if "alcool" in t or "ivresse" in t or "alcoolémie" in t or "drogue" in t or "stupéfiant" in t or "g/l" in t or "cannabis" in t:
        return "scene", "alcohol_scene", "Alcool, drogues et conduite"
    if "premiers secours" in t or "arrêt cardiaque" in t or "massage cardiaque" in t or "pls" in t or "position latérale" in t or "hémorragie" in t or "brûlure" in t or "fracture" in t or "blessé" in t or "accident" in t:
        return "scene", "first_aid", "Premiers secours"
    if "somnolence" in t or "fatigue" in t or "endormir" in t:
        return "scene", "night_driving", "Somnolence au volant"

    # ═══ FALLBACKS PAR CATÉGORIE (variés, non répétitifs) ═════════════════
    if category == "signalisation":
        # Répartir sur plusieurs panneaux selon un hash du texte
        panels = ["stop", "give_way", "no_entry", "priority", "roundabout",
                  "pedestrian_crossing", "danger_generic", "no_overtaking"]
        return "sign", panels[_stable_hash(text) % len(panels)], "Signalisation routière"
    if category == "vitesse":
        speeds = ["speed_50", "speed_90", "speed_30", "speed_110", "speed_70"]
        return "sign", speeds[_stable_hash(text) % len(speeds)], "Limitation de vitesse"
    if category == "priorites":
        return "scene", "intersection_priority_right", "Règles de priorité"
    if category == "depassement":
        return "sign", "no_overtaking", "Règles de dépassement"
    if category == "alcool_drogues":
        return "scene", "alcohol_scene", "Alcool, drogues et conduite"
    if category == "premiers_secours":
        return "scene", "first_aid", "Premiers secours"
    if category == "urgence":
        return "scene", "situation_emergency_vehicle", "Situation d'urgence"
    if category == "securite_passive":
        return "scene", "situation_safe_distance", "Sécurité et distances"

    return None, None, None

def seed_questions(db) -> list[Question]:
    """
    Charge les 200 questions dans la base de données.

    Répartition :
      40 questions officielles (QUESTIONS_GN) : pool examen DNTT
     160 questions entraînement (QUESTIONS_TRAINING_FULL) : mode entraînement libre

    L'exam_engine tire toujours 40 questions parmi les 200 actives,
    selon la répartition officielle par catégorie (CATEGORY_DISTRIBUTION).
    Avec 200 questions en banque, chaque examen est vraiment unique.
    """
    existing = db.scalars(select(Question).where(Question.is_active.is_(True))).all()
    if len(existing) >= 200:
        print(f"  ✅ {len(existing)} questions en banque (200 déjà présentes)")
        return list(existing)

    # Désactiver les anciennes questions si migration depuis 40 → 200
    if 0 < len(existing) < 200:
        print(f"  ↳ Migration banque : {len(existing)} → 200 questions")
        # Conserver les anciennes actives, ajouter les manquantes
        existing_texts = {q.text for q in existing}
        all_bank = QUESTIONS_GN + QUESTIONS_TRAINING_FULL
        to_add = [q for q in all_bank if q["text"] not in existing_texts]
        questions_out = list(existing)
        for q in to_add:
            _mtype, _murl, _malt = _get_media_for_question(q["text"], q["category"])
            obj = Question(
                category=q["category"],
                text=q["text"],
                options=q["options"],
                correct_answer=q["correct_answer"],
                explanation=q.get("explanation", ""),
                media_type=_mtype,
                media_url=_murl,
                media_alt=_malt,
                is_active=True,
                validation_status="approved",
            )
            db.add(obj)
            questions_out.append(obj)
        db.commit()
        for q in questions_out:
            db.refresh(q)
        print(f"  ✅ {len(questions_out)} questions en banque ({len(to_add)} ajoutées)")
        return questions_out

    # Premier seed : charger toutes les 200 questions
    all_bank = QUESTIONS_GN + QUESTIONS_TRAINING_FULL  # 200 questions
    questions = []
    for q in all_bank:
        _mtype, _murl, _malt = _get_media_for_question(q["text"], q["category"])
        obj = Question(
            category=q["category"],
            text=q["text"],
            options=q["options"],
            correct_answer=q["correct_answer"],
            explanation=q.get("explanation", ""),
            media_type=_mtype,
            media_url=_murl,
            media_alt=_malt,
            is_active=True,
            validation_status="approved",
        )
        db.add(obj)
        questions.append(obj)
    db.commit()
    for q in questions:
        db.refresh(q)
    print(f"  ✅ {len(questions)} questions créées (40 officielles + 160 entraînement)")
    return questions


# ── SESSIONS ──────────────────────────────────────────────────────────────

def seed_sessions(db, centers: dict[str, Center]) -> list[ExamSession]:
    """
    Génère 3 sessions par semaine pour les 3 centres pilotes de Conakry.
    Démontre la capacité à gérer des sessions simultanées dans plusieurs centres.

    Règles appliquées :
      - 35 candidats max par session
      - 3 sessions max par semaine par centre
      - Sessions simultanées autorisées dans des centres différents
    """
    from datetime import timedelta
    now = datetime.now(UTC).replace(tzinfo=None)

    # Sessions simultanées dans les 13 communes de Conakry
    # Règle DNTT : max 35 candidats/session, max 3 sessions/semaine/centre
    # Sessions simultanées AUTORISÉES dans des centres DIFFÉRENTS
    PILOT_CENTERS = [
        # Communes historiques (5)
        "CRG-KAL-001", "CRG-DIX-001", "CRG-RAT-001", "CRG-MAT-001", "CRG-MTO-001",
        # Nouvelles communes CNT 2024 (8)
        "CRG-LAM-001", "CRG-GBS-001", "CRG-SON-001", "CRG-TOM-001",
        "CRG-KAK-001", "CRG-KOL-001", "CRG-NON-001", "CRG-COS-001",
    ]

    session_defs = []
    for week in range(3):  # 3 semaines de données
        for day_offset, day_name in [(7, "lundi"), (9, "mercredi"), (11, "vendredi")]:
            for ci, center_code in enumerate(PILOT_CENTERS):
                if center_code not in centers:
                    continue
                ref = f"GN-SESSION-2026-{center_code[-7:]}-W{week+1}-{day_name.upper()[:3]}"
                session_defs.append({
                    "reference": ref,
                    "center_code": center_code,
                    "starts_at": now + timedelta(days=day_offset + week * 7, hours=ci),
                    "capacity": 35,
                })

    # Ajouter les sessions des semaines passées (pour les candidats déjà examinés)
    for ci, center_code in enumerate(PILOT_CENTERS):
        if center_code not in centers:
            continue
        session_defs.extend([
            {
                "reference": f"GN-SESSION-2026-{center_code[-7:]}-PAST-1",
                "center_code": center_code,
                "starts_at": now - timedelta(days=14 - ci),
                "capacity": 35,
            },
            {
                "reference": f"GN-SESSION-2026-{center_code[-7:]}-PAST-2",
                "center_code": center_code,
                "starts_at": now - timedelta(days=7 - ci),
                "capacity": 35,
            },
        ])

    sessions = []
    for s in session_defs:
        if s["center_code"] not in centers:
            continue
        existing = db.scalar(
            select(ExamSession).where(ExamSession.reference == s["reference"])
        )
        if existing:
            sessions.append(existing)
            continue
        session = ExamSession(
            reference=s["reference"],
            center_id=centers[s["center_code"]].id,
            starts_at=s["starts_at"],
            capacity=s["capacity"],
            status="planned" if s["starts_at"] > now else "closed",
        )
        db.add(session)
        db.flush()
        sessions.append(session)
    db.commit()
    print(f"  ✅ {len(sessions)} sessions planifiées")
    print("     13 communes Conakry × 3 sessions/semaine × 2 centres pilotes/commune")
    print("     Sessions simultanées activées : plusieurs centres le même jour/heure")
    print(f"     Capacité totale : {len(sessions) * 35} places disponibles")
    return sessions

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


CANDIDATES_DATA = [
    {
        "reference": "GN-CAND-2026-001",
        "first_name": "Mamadou",
        "last_name": "Diallo",
        "identity_number": "GN-NINA-2026-000001",
        "phone": "+224620000001",
        "permit_category": "B",
        "scenario": "admitted",
        "score": 38,
        "session_index": 0,
    },
    {
        "reference": "GN-CAND-2026-002",
        "first_name": "Fatoumata",
        "last_name": "Camara",
        "identity_number": "GN-NINA-2026-000002",
        "phone": "+224620000002",
        "permit_category": "B",
        "scenario": "failed",
        "score": 28,
        "session_index": 0,
    },
    {
        "reference": "GN-CAND-2026-003",
        "first_name": "Alpha",
        "last_name": "Bah",
        "identity_number": "GN-NINA-2026-000003",
        "phone": "+224620000003",
        "permit_category": "B",
        "scenario": "admitted",
        "score": 40,
        "session_index": 0,
    },
    {
        "reference": "GN-CAND-2026-004",
        "first_name": "Mariam",
        "last_name": "Soumah",
        "identity_number": "GN-NINA-2026-000004",
        "phone": "+224620000004",
        "permit_category": "B",
        "scenario": "paid_future",
        "score": None,
        "session_index": 1,
    },
    {
        "reference": "GN-CAND-2026-005",
        "first_name": "Ibrahima",
        "last_name": "Kouyaté",
        "identity_number": "GN-NINA-2026-000005",
        "phone": "+224620000005",
        "permit_category": "B",
        "scenario": "booked_unpaid",
        "score": None,
        "session_index": 1,
    },
    {
        "reference": "GN-CAND-2026-006",
        "first_name": "Kadiatou",
        "last_name": "Sylla",
        "identity_number": "GN-NINA-2026-000006",
        "phone": "+224660000006",
        "permit_category": "B",
        "scenario": "admitted",
        "score": 36,
        "session_index": 0,
    },
    {
        "reference": "GN-CAND-2026-007",
        "first_name": "Oumar",
        "last_name": "Baldé",
        "identity_number": "GN-NINA-2026-000007",
        "phone": "+224660000007",
        "permit_category": "B",
        "scenario": "registered_only",
        "score": None,
        "session_index": None,
    },
    {
        "reference": "GN-CAND-2026-008",
        "first_name": "Aminata",
        "last_name": "Condé",
        "identity_number": "GN-NINA-2026-000008",
        "phone": "+224660000008",
        "permit_category": "B",
        "scenario": "failed",
        "score": 34,
        "session_index": 0,
    },
]


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
