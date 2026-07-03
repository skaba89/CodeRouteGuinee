#!/usr/bin/env bash
# entrypoint.sh — CodeRoute Guinée
# Auto-setup au démarrage : migrations + seed admin + Gunicorn
set -e

echo "════════════════════════════════════════════"
echo "  CodeRoute Guinée — Démarrage"
echo "  Environnement : ${ENVIRONMENT:-development}"
echo "════════════════════════════════════════════"

# Vérification DATABASE_URL
if [ -z "${DATABASE_URL:-}" ] || echo "${DATABASE_URL}" | grep -q "CHANGE_ME"; then
    echo "⚠️  DATABASE_URL non configurée — définir dans Render Dashboard"
fi

# ── 1. Migrations Alembic ─────────────────────────────────────────
if [ -n "${DATABASE_URL:-}" ] && ! echo "${DATABASE_URL}" | grep -q "CHANGE_ME"; then
    echo "── Migrations Alembic ──"
    MIGRATE_URL="${ALEMBIC_DATABASE_URL:-$DATABASE_URL}"
    DATABASE_URL="$MIGRATE_URL" alembic upgrade head && echo "✅ Migrations OK" || \
        echo "⚠️  Migrations échouées — le serveur démarre quand même"
fi

# ── 2. Seed admin (si BOOTSTRAP_ADMIN_PASSWORD défini) ───────────
if [ -n "${BOOTSTRAP_ADMIN_PASSWORD:-}" ] && [ -n "${DATABASE_URL:-}" ] && \
   ! echo "${DATABASE_URL}" | grep -q "CHANGE_ME"; then
    echo "── Bootstrap admin ──"
    python3 - << 'PYEOF'
import os, sys, logging, uuid
logging.basicConfig(level=logging.WARNING)

try:
    from app.db.session import SessionLocal
    from app.models_user import User
    from app.security import get_password_hash
    from sqlalchemy import select

    ADMIN_EMAIL    = os.environ.get("BOOTSTRAP_ADMIN_EMAIL", "super_admin@coderoute.gov.gn")
    ADMIN_PASSWORD = os.environ.get("BOOTSTRAP_ADMIN_PASSWORD", "")
    ADMIN_NAME     = os.environ.get("BOOTSTRAP_ADMIN_NAME", "Directeur National CodeRoute")

    if not ADMIN_PASSWORD:
        print("⏭️  BOOTSTRAP_ADMIN_PASSWORD vide — seed ignoré")
        sys.exit(0)

    db = SessionLocal()
    existing = db.execute(select(User).where(User.email == ADMIN_EMAIL)).scalar_one_or_none()
    if existing:
        print(f"✅ Admin déjà présent : {ADMIN_EMAIL}")
    else:
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
    db.close()
except Exception as e:
    print(f"⚠️  Seed admin ignoré : {e}", file=sys.stderr)
PYEOF
fi

# ── 3. Seed questions (si DB disponible) ─────────────────────────
if [ -n "${DATABASE_URL:-}" ] && ! echo "${DATABASE_URL}" | grep -q "CHANGE_ME"; then
    python3 - << 'PYEOF'
import sys, logging
logging.basicConfig(level=logging.WARNING)
try:
    from app.db.session import SessionLocal
    from app.models_question import Question
    from app.models_center import Center
    db = SessionLocal()
    n_q = db.query(Question).count()
    n_c = db.query(Center).count()
    if n_q < 50:
        from app.seed_full import seed_questions
        questions = seed_questions(db); db.commit()
        print(f"✅ Questions insérées : {len(questions)}")
    else:
        print(f"✅ Questions : {n_q} déjà présentes")
    if n_c < 1:
        from app.seed_full import seed_centers
        centers = seed_centers(db); db.commit()
        print(f"✅ Centres insérés : {len(centers)}")
    else:
        print(f"✅ Centres : {n_c} déjà présents")
    db.close()
except Exception as e:
    print(f"⚠️  Seed ignoré : {e}", file=sys.stderr)
PYEOF
fi

# ── 4. Démarrage Gunicorn ─────────────────────────────────────────
echo "── Démarrage Gunicorn ──"
exec gunicorn app.main:app -c gunicorn.conf.py
