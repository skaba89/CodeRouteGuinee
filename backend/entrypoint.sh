#!/usr/bin/env bash
# entrypoint.sh — CodeRoute Guinée
# P10 : migrations pre-deploy et seeds désactivés par défaut en production HA.
set -euo pipefail

ENVIRONMENT_VALUE="${ENVIRONMENT:-development}"
RUN_MIGRATIONS_ON_STARTUP_VALUE="${RUN_MIGRATIONS_ON_STARTUP:-}"
RUN_BOOTSTRAP_SEED_ON_STARTUP_VALUE="${RUN_BOOTSTRAP_SEED_ON_STARTUP:-}"

if [ -z "$RUN_MIGRATIONS_ON_STARTUP_VALUE" ]; then
    if [ "$ENVIRONMENT_VALUE" = "production" ]; then
        RUN_MIGRATIONS_ON_STARTUP_VALUE=false
    else
        RUN_MIGRATIONS_ON_STARTUP_VALUE=true
    fi
fi
if [ -z "$RUN_BOOTSTRAP_SEED_ON_STARTUP_VALUE" ]; then
    if [ "$ENVIRONMENT_VALUE" = "production" ]; then
        RUN_BOOTSTRAP_SEED_ON_STARTUP_VALUE=false
    else
        RUN_BOOTSTRAP_SEED_ON_STARTUP_VALUE=true
    fi
fi

echo "════════════════════════════════════════════"
echo "  CodeRoute Guinée — Démarrage"
echo "  Environnement : ${ENVIRONMENT_VALUE}"
echo "════════════════════════════════════════════"

# Vérification DATABASE_URL
if [ -z "${DATABASE_URL:-}" ] || echo "${DATABASE_URL}" | grep -q "CHANGE_ME"; then
    echo "⚠️  DATABASE_URL non configurée — définir dans le gestionnaire d'environnement"
fi

# ── 1. Migrations Alembic ─────────────────────────────────────────
if [ "$RUN_MIGRATIONS_ON_STARTUP_VALUE" = "true" ]; then
    echo "── Migrations Alembic au startup (mode explicite/dev) ──"
    ./scripts/predeploy.sh
else
    echo "✅ Migrations au startup désactivées — pre-deploy fail-closed requis."
fi

# ── 2. Seed admin (mode explicite uniquement en production HA) ────
if [ "$RUN_BOOTSTRAP_SEED_ON_STARTUP_VALUE" = "true" ] && \
   [ -n "${BOOTSTRAP_ADMIN_PASSWORD:-}" ] && [ -n "${DATABASE_URL:-}" ] && \
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
    try:
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
    finally:
        db.close()
except Exception as e:
    print(f"❌ Seed admin échoué : {e.__class__.__name__}", file=sys.stderr)
    raise
PYEOF
fi

# ── 3. Seed questions/centres (mode explicite uniquement) ─────────
if [ "$RUN_BOOTSTRAP_SEED_ON_STARTUP_VALUE" = "true" ] && \
   [ -n "${DATABASE_URL:-}" ] && ! echo "${DATABASE_URL}" | grep -q "CHANGE_ME"; then
    python3 - << 'PYEOF'
import logging
logging.basicConfig(level=logging.WARNING)
from app.db.session import SessionLocal
from app.models_question import Question
from app.models_center import Center

db = SessionLocal()
try:
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
finally:
    db.close()
PYEOF
else
    echo "✅ Seeds au startup désactivés — aucune course entre instances HA."
fi

# ── 4. Prometheus multiprocess ─────────────────────────────────────
# Le chemin est volontairement borné/hardcodé pour éviter tout rm -rf sur
# une valeur d'environnement mal configurée. Il est local à chaque instance.
if [ "${METRICS_ENABLED:-false}" = "true" ]; then
    export PROMETHEUS_MULTIPROC_DIR="/tmp/coderoute-prometheus"
    rm -rf -- "$PROMETHEUS_MULTIPROC_DIR"
    mkdir -p "$PROMETHEUS_MULTIPROC_DIR"
    chmod 0700 "$PROMETHEUS_MULTIPROC_DIR"
else
    unset PROMETHEUS_MULTIPROC_DIR || true
fi

# ── 5. Démarrage Gunicorn ─────────────────────────────────────────
echo "── Démarrage Gunicorn ──"
exec gunicorn app.main:app -c gunicorn.conf.py
