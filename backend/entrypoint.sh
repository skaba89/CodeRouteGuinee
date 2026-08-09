#!/usr/bin/env bash
# entrypoint.sh — CodeRoute Guinée P10
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

if [ "$RUN_MIGRATIONS_ON_STARTUP_VALUE" = "true" ]; then
  echo "── Migrations Alembic au startup (mode explicite/dev) ──"
  ./scripts/predeploy.sh
else
  echo "✅ Migrations au startup désactivées — utiliser le pre-deploy fail-closed."
fi

if [ "$RUN_BOOTSTRAP_SEED_ON_STARTUP_VALUE" = "true" ]; then
  if [ -n "${BOOTSTRAP_ADMIN_PASSWORD:-}" ] && [ -n "${DATABASE_URL:-}" ] && [[ "${DATABASE_URL}" != *"CHANGE_ME"* ]]; then
    echo "── Bootstrap admin ──"
    python3 - << 'PYEOF'
import os, sys, logging, uuid
logging.basicConfig(level=logging.WARNING)
try:
    from app.db.session import SessionLocal
    from app.models_user import User
    from app.security import get_password_hash
    from sqlalchemy import select

    email = os.environ.get("BOOTSTRAP_ADMIN_EMAIL", "super_admin@coderoute.gov.gn")
    password = os.environ.get("BOOTSTRAP_ADMIN_PASSWORD", "")
    name = os.environ.get("BOOTSTRAP_ADMIN_NAME", "Directeur National CodeRoute")
    if not password:
        sys.exit(0)
    db = SessionLocal()
    existing = db.execute(select(User).where(User.email == email)).scalar_one_or_none()
    if not existing:
        db.add(User(
            id=str(uuid.uuid4()),
            email=email,
            full_name=name,
            password_hash=get_password_hash(password),
            role="super_admin",
            is_active=True,
        ))
        db.commit()
        print("✅ Admin bootstrap créé")
    else:
        print("✅ Admin bootstrap déjà présent")
    db.close()
except Exception as exc:
    print(f"ERROR: bootstrap admin échoué: {exc.__class__.__name__}", file=sys.stderr)
    raise
PYEOF
  fi

  if [ -n "${DATABASE_URL:-}" ] && [[ "${DATABASE_URL}" != *"CHANGE_ME"* ]]; then
    echo "── Seed initial contrôlé ──"
    python3 - << 'PYEOF'
from app.db.session import SessionLocal
from app.models_question import Question
from app.models_center import Center

db = SessionLocal()
try:
    n_q = db.query(Question).count()
    n_c = db.query(Center).count()
    if n_q < 50:
        from app.seed_full import seed_questions
        seed_questions(db)
        db.commit()
    if n_c < 1:
        from app.seed_full import seed_centers
        seed_centers(db)
        db.commit()
finally:
    db.close()
PYEOF
  fi
else
  echo "✅ Seeds au startup désactivés — aucune course entre instances HA."
fi

echo "── Démarrage Gunicorn ──"
exec gunicorn app.main:app -c gunicorn.conf.py
