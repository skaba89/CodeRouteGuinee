"""
Seed pilote Conakry — Centre unique, 50 candidats Permis B, paiement espèces.
À exécuter UNE SEULE FOIS sur la base Neon de production du pilote.

Usage :
    cd /app && python -c "from app.seed_pilote_conakry import run; run()"
"""
from __future__ import annotations
import logging
from datetime import date, timedelta
from app.db.session import SessionLocal
from app.models_candidate import Candidate
from app.models_user import User
from app.models_center import Center as ExamCenter
from app.models_question import Question
from app.seed_full import seed_questions
import uuid, hashlib, os

log = logging.getLogger("seed.pilote")


# ── Centre pilote ───────────────────────────────────────────────────────────
CENTRE_PILOTE = {
    "id":          str(uuid.uuid4()),
    "name":        "Centre DNTT Kaloum — Pilote Conakry",
    "code":        "GN-CKY-KALOUM-01",
    "city":        "Conakry",
    "prefecture":  "Conakry",
    "commune":     "Kaloum",
    "address":     "Direction Nationale des Transports Terrestres, Kaloum, Conakry",
    "capacity":    35,  # max DNTT par session
    "is_active":   True,
}

# ── Compte admin centre ─────────────────────────────────────────────────────
ADMIN_CENTRE = {
    "email":        "centre.kaloum@dntt.gov.gn",
    "full_name":    "Chef Centre DNTT Kaloum",
    "role":         "center",
    "is_active":    True,
    "password_raw": os.environ.get("PILOT_CENTER_PASSWORD", "KaloumDNTT2024!"),
}

# ── 50 candidats pilote ─────────────────────────────────────────────────────
CANDIDATS_PILOTE = [
    # Format : (prenom, nom, telephone, nni_fictif)
    ("Mamadou",    "Diallo",     "+224621000001", "GN001"),
    ("Fatoumata",  "Bah",        "+224621000002", "GN002"),
    ("Ibrahim",    "Sow",        "+224621000003", "GN003"),
    ("Mariama",    "Barry",      "+224621000004", "GN004"),
    ("Amadou",     "Camara",     "+224621000005", "GN005"),
    ("Aissatou",   "Diallo",     "+224621000006", "GN006"),
    ("Oumar",      "Baldé",      "+224621000007", "GN007"),
    ("Kadiatou",   "Sylla",      "+224621000008", "GN008"),
    ("Seydou",     "Condé",      "+224621000009", "GN009"),
    ("Hawa",       "Kouyaté",    "+224621000010", "GN010"),
    ("Alpha",      "Touré",      "+224621000011", "GN011"),
    ("Mariam",     "Keïta",      "+224621000012", "GN012"),
    ("Souleymane", "Doumbouya",  "+224621000013", "GN013"),
    ("Aminata",    "Conté",      "+224621000014", "GN014"),
    ("Moussa",     "Traoré",     "+224621000015", "GN015"),
    ("Safiatou",   "Guilavogui", "+224621000016", "GN016"),
    ("Aboubacar",  "Konaté",     "+224621000017", "GN017"),
    ("Djenabou",   "Millimono",  "+224621000018", "GN018"),
    ("Boubacar",   "Balde",      "+224621000019", "GN019"),
    ("Nene",       "Camara",     "+224621000020", "GN020"),
    ("Lansana",    "Soumah",     "+224621000021", "GN021"),
    ("Maimouna",   "Kourouma",   "+224621000022", "GN022"),
    ("Cellou",     "Diallo",     "+224621000023", "GN023"),
    ("Hadja",      "Bah",        "+224621000024", "GN024"),
    ("Aliou",      "Sow",        "+224621000025", "GN025"),
    ("Marème",     "Barry",      "+224621000026", "GN026"),
    ("Sory",       "Camara",     "+224621000027", "GN027"),
    ("Fatouma",    "Kouyaté",    "+224621000028", "GN028"),
    ("Elhadj",     "Touré",      "+224621000029", "GN029"),
    ("Gnalen",     "Diallo",     "+224621000030", "GN030"),
    ("Thierno",    "Baldé",      "+224621000031", "GN031"),
    ("Ramata",     "Condé",      "+224621000032", "GN032"),
    ("Bangaly",    "Konaté",     "+224621000033", "GN033"),
    ("Djènè",      "Sylla",      "+224621000034", "GN034"),
    ("Ibrahima",   "Traoré",     "+224621000035", "GN035"),
    ("Kadia",      "Guilavogui", "+224621000036", "GN036"),
    ("Ousmane",    "Keïta",      "+224621000037", "GN037"),
    ("Bintou",     "Millimono",  "+224621000038", "GN038"),
    ("Cheick",     "Doumbouya",  "+224621000039", "GN039"),
    ("Rokia",      "Soumah",     "+224621000040", "GN040"),
    ("Tidiane",    "Kourouma",   "+224621000041", "GN041"),
    ("Maïmouna",   "Conté",      "+224621000042", "GN042"),
    ("Saliou",     "Camara",     "+224621000043", "GN043"),
    ("Fatou",      "Bah",        "+224621000044", "GN044"),
    ("Morlaye",    "Diallo",     "+224621000045", "GN045"),
    ("Fanta",      "Sow",        "+224621000046", "GN046"),
    ("Saïdou",     "Barry",      "+224621000047", "GN047"),
    ("Kadja",      "Touré",      "+224621000048", "GN048"),
    ("Kemoko",     "Kouyaté",    "+224621000049", "GN049"),
    ("Aïcha",      "Baldé",      "+224621000050", "GN050"),
]


def _hash_password(raw: str) -> str:
    from passlib.context import CryptContext
    ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
    return ctx.hash(raw)


def run():
    db = SessionLocal()
    try:
        log.info("=== SEED PILOTE CONAKRY ===")

        # 1. Questions (200 Permis B)
        existing_q = db.query(Question).count()
        if existing_q < 10:
            log.info("Seed questions...")
            questions = seed_questions(db)
            db.commit()
            log.info("✅ %d questions insérées", len(questions))
        else:
            log.info("✅ Questions déjà présentes (%d)", existing_q)

        # 2. Centre pilote
        existing_c = db.query(ExamCenter).filter_by(code=CENTRE_PILOTE["code"]).first()
        if not existing_c:
            centre = ExamCenter(**{k: v for k, v in CENTRE_PILOTE.items() if k != 'id'})
            centre.id = CENTRE_PILOTE["id"]
            db.add(centre)
            db.commit()
            db.refresh(centre)
            log.info("✅ Centre pilote créé : %s", centre.name)
        else:
            centre = existing_c
            log.info("✅ Centre déjà présent : %s", centre.name)

        # 3. Admin centre
        existing_u = db.query(User).filter_by(email=ADMIN_CENTRE["email"]).first()
        if not existing_u:
            user = User(
                id=str(uuid.uuid4()),
                email=ADMIN_CENTRE["email"],
                full_name=ADMIN_CENTRE["full_name"],
                hashed_password=_hash_password(ADMIN_CENTRE["password_raw"]),
                role=ADMIN_CENTRE["role"],
                is_active=True,
                center_id=centre.id if hasattr(centre, 'id') else None,
            )
            db.add(user)
            db.commit()
            log.info("✅ Admin centre créé : %s", ADMIN_CENTRE["email"])
        else:
            log.info("✅ Admin centre déjà présent")

        # 4. Candidats pilote
        created = 0
        for prenom, nom, tel, nni in CANDIDATS_PILOTE:
            existing = db.query(Candidate).filter_by(phone=tel).first()
            if not existing:
                ref = f"GN-CODE-B-PILOT-{nni}"
                cand = Candidate(
                    id=str(uuid.uuid4()),
                    first_name=prenom,
                    last_name=nom,
                    phone=tel,
                    identity_number=nni,
                    permit_category="B",
                    status="registered",
                    reference=ref,
                    attempt_count=0,
                )
                db.add(cand)
                created += 1
        db.commit()
        log.info("✅ %d candidats pilote créés", created)

        # Résumé
        total_c = db.query(Candidate).count()
        total_q = db.query(Question).count()
        print(f"""
╔══════════════════════════════════════════════════════════╗
║  PILOTE CONAKRY — SEED TERMINÉ                          ║
╠══════════════════════════════════════════════════════════╣
║  Questions Permis B  : {total_q:<5} (200 attendues)        ║
║  Centre pilote       : {centre.name[:30]:<30} ║
║  Candidats pilote    : {total_c:<5} / 50                    ║
║  Login admin centre  : {ADMIN_CENTRE['email']:<32} ║
╚══════════════════════════════════════════════════════════╝
""")
    except Exception as e:
        db.rollback()
        log.error("❌ Erreur seed pilote : %s", e)
        raise
    finally:
        db.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run()
