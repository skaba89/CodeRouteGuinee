#!/usr/bin/env bash
# entrypoint.sh — CodeRoute Guinée
# Auto-setup complet : migrations + seed + admin + Gunicorn
# Aucune action manuelle requise.
set -e

echo "════════════════════════════════════════════"
echo "  CodeRoute Guinée — Démarrage Production"
echo "  Environnement : ${ENVIRONMENT:-development}"
echo "════════════════════════════════════════════"

# ── Vérification DATABASE_URL ─────────────────
if [ -z "${DATABASE_URL:-}" ]; then
    echo "❌ ERREUR CRITIQUE : DATABASE_URL non définie."
    echo "   → Render Dashboard → coderoute-backend → Environment"
    echo "   → Ajouter DATABASE_URL = postgresql+psycopg://..."
    echo "   Le serveur démarre quand même (toutes les requêtes DB retourneront 503)."
fi

# ── 1. Migrations Alembic ─────────────────────
if [ -n "${DATABASE_URL:-}" ]; then
    echo ""
    echo "── 1. Migrations Alembic ──"
    MIGRATE_URL="${ALEMBIC_DATABASE_URL:-$DATABASE_URL}"
    if DATABASE_URL="$MIGRATE_URL" alembic upgrade head 2>&1; then
        echo "✅ Migrations OK"
    else
        echo "⚠️  Migrations échouées — le serveur démarre quand même"
    fi
fi

# ── 2. Auto-seed (idempotent) ─────────────────
if [ -n "${DATABASE_URL:-}" ]; then
    echo ""
    echo "── 2. Initialisation données (idempotent) ──"
    python3 - << 'PYEOF'
import logging, sys, os
logging.basicConfig(level=logging.WARNING)  # silencieux sauf erreurs

try:
    from app.db.session import SessionLocal
    from app.models_user import User
    from app.models_question import Question
    from app.models_center import Center
    from sqlalchemy import select

    db = SessionLocal()

    # ── Questions ──────────────────────────────────
    q_count = db.execute(select(User).where(User.email.isnot(None))).scalars().all()
    n_questions = db.query(Question).count()
    if n_questions < 50:
        from app.seed_full import seed_questions
        questions = seed_questions(db)
        db.commit()
        print(f"✅ Questions : {len(questions)} insérées")
    else:
        print(f"✅ Questions : {n_questions} déjà présentes")

    # ── Centres ────────────────────────────────────
    n_centers = db.query(Center).count()
    if n_centers < 1:
        from app.seed_full import seed_centers
        centers = seed_centers(db)
        db.commit()
        print(f"✅ Centres : {len(centers)} insérés")
    else:
        print(f"✅ Centres : {n_centers} déjà présents")

    # ── Admin super_admin ──────────────────────────
    from app.security import get_password_hash
    import uuid

    ADMIN_EMAIL = os.environ.get("BOOTSTRAP_ADMIN_EMAIL", "super_admin@coderoute.gov.gn")
    ADMIN_PASSWORD = os.environ.get("BOOTSTRAP_ADMIN_PASSWORD", "CodeRoute2026!")
    ADMIN_NAME = os.environ.get("BOOTSTRAP_ADMIN_NAME", "Directeur National CodeRoute")

    existing = db.execute(select(User).where(User.email == ADMIN_EMAIL)).scalar_one_or_none()
    if not existing:
        admin = User(
            id=str(uuid.uuid4()),
            email=ADMIN_EMAIL,
            full_name=ADMIN_NAME,
            password_hash=get_password_hash(ADMIN_PASSWORD),
            role="super_admin",
            is_active=True,
        )
        db.add(admin)
        db.commit()
        print(f"✅ Admin créé : {ADMIN_EMAIL}")
    else:
        print(f"✅ Admin déjà présent : {ADMIN_EMAIL}")

    db.close()
    print("✅ Initialisation terminée")

except Exception as e:
    print(f"⚠️  Init partielle : {e}", file=sys.stderr)
    # Ne pas bloquer le démarrage
PYEOF
fi

# ── 3. Démarrage Gunicorn ─────────────────────
echo ""
echo "── 3. Démarrage Gunicorn ──"
echo ""
exec gunicorn app.main:app -c gunicorn.conf.py
