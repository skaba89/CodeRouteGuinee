#!/usr/bin/env bash
set -euo pipefail

ENVIRONMENT_VALUE="${ENVIRONMENT:-development}"
RUN_MIGRATIONS_ON_STARTUP_VALUE="${RUN_MIGRATIONS_ON_STARTUP:-}"
RUN_BOOTSTRAP_SEED_ON_STARTUP_VALUE="${RUN_BOOTSTRAP_SEED_ON_STARTUP:-}"

if [ -z "$RUN_MIGRATIONS_ON_STARTUP_VALUE" ]; then
  [ "$ENVIRONMENT_VALUE" = "production" ] && RUN_MIGRATIONS_ON_STARTUP_VALUE=false || RUN_MIGRATIONS_ON_STARTUP_VALUE=true
fi
if [ -z "$RUN_BOOTSTRAP_SEED_ON_STARTUP_VALUE" ]; then
  [ "$ENVIRONMENT_VALUE" = "production" ] && RUN_BOOTSTRAP_SEED_ON_STARTUP_VALUE=false || RUN_BOOTSTRAP_SEED_ON_STARTUP_VALUE=true
fi

echo "CodeRoute Guinée — démarrage (${ENVIRONMENT_VALUE})"

if [ "$RUN_MIGRATIONS_ON_STARTUP_VALUE" = "true" ]; then
  echo "Migrations Alembic au startup (mode explicite/dev)"
  ./scripts/predeploy.sh
else
  echo "Migrations startup désactivées — pre-deploy requis."
fi

if [ "$RUN_BOOTSTRAP_SEED_ON_STARTUP_VALUE" = "true" ]; then
  if [ -n "${BOOTSTRAP_ADMIN_PASSWORD:-}" ] && [ -n "${DATABASE_URL:-}" ] && [[ "${DATABASE_URL}" != *"CHANGE_ME"* ]]; then
    python3 - <<'PY'
import os, uuid
from sqlalchemy import select
from app.db.session import SessionLocal
from app.models_user import User
from app.security import get_password_hash

email = os.environ.get("BOOTSTRAP_ADMIN_EMAIL", "super_admin@coderoute.gov.gn")
password = os.environ.get("BOOTSTRAP_ADMIN_PASSWORD", "")
name = os.environ.get("BOOTSTRAP_ADMIN_NAME", "Directeur National CodeRoute")
if password:
    db = SessionLocal()
    try:
        existing = db.execute(select(User).where(User.email == email)).scalar_one_or_none()
        if not existing:
            db.add(User(id=str(uuid.uuid4()), email=email, full_name=name, password_hash=get_password_hash(password), role="super_admin", is_active=True))
            db.commit()
    finally:
        db.close()
PY
  fi

  if [ -n "${DATABASE_URL:-}" ] && [[ "${DATABASE_URL}" != *"CHANGE_ME"* ]]; then
    python3 - <<'PY'
from app.db.session import SessionLocal
from app.models_question import Question
from app.models_center import Center

db = SessionLocal()
try:
    if db.query(Question).count() < 50:
        from app.seed_full import seed_questions
        seed_questions(db)
        db.commit()
    if db.query(Center).count() < 1:
        from app.seed_full import seed_centers
        seed_centers(db)
        db.commit()
finally:
    db.close()
PY
  fi
else
  echo "Seeds startup désactivés — aucune course entre instances HA."
fi

exec gunicorn app.main:app -c gunicorn.conf.py
