#!/usr/bin/env bash
# setup_prod.sh — Configuration one-shot depuis Render Shell
# À lancer UNE SEULE FOIS après avoir défini DATABASE_URL dans Render
# Usage : bash scripts/setup_prod.sh

set -e
cd /app

echo "═══════════════════════════════════════════════"
echo "  CodeRoute Guinée — Setup Production One-Shot"
echo "═══════════════════════════════════════════════"
echo ""

# Vérifications préalables
if [ -z "${DATABASE_URL:-}" ]; then
    echo "❌ ERREUR : DATABASE_URL non définie."
    echo "   Configurez-la dans Render Dashboard d'abord."
    exit 1
fi

echo "✅ DATABASE_URL présente"

# 1. Migrations Alembic
echo ""
echo "── 1. Migrations Alembic ──"
if [ -n "${ALEMBIC_DATABASE_URL:-}" ]; then
    DATABASE_URL="$ALEMBIC_DATABASE_URL" alembic upgrade head
else
    alembic upgrade head
fi
echo "✅ Migrations appliquées"

# 2. Seed questions (200 Permis B)
echo ""
echo "── 2. Seed questions Permis B ──"
python3 -c "
import logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s %(message)s')
from app.db.session import SessionLocal
from app.models_question import Question
db = SessionLocal()
count = db.query(Question).count()
if count >= 100:
    print(f'✅ {count} questions déjà en base — seed ignoré')
else:
    from app.seed_full import seed_questions
    questions = seed_questions(db)
    db.commit()
    print(f'✅ {len(questions)} questions insérées')
db.close()
"

# 3. Bootstrap admin DNTT
echo ""
echo "── 3. Bootstrap admin DNTT ──"
python3 -c "
import os, logging
logging.basicConfig(level=logging.INFO)
email = os.environ.get('BOOTSTRAP_ADMIN_EMAIL', 'admin@dntt.gov.gn')
password = os.environ.get('BOOTSTRAP_ADMIN_PASSWORD')
if not password:
    import secrets
    password = secrets.token_urlsafe(16)
    print(f'⚠️  BOOTSTRAP_ADMIN_PASSWORD non défini')
    print(f'   Mot de passe généré : {password}')
    print(f'   SAUVEGARDEZ CE MOT DE PASSE !')

from app.db.session import SessionLocal
from app.models_user import User
from app.security import get_password_hash
from sqlalchemy import select
import uuid

db = SessionLocal()
existing = db.execute(select(User).where(User.email == email)).scalar_one_or_none()
if existing:
    print(f'✅ Admin déjà présent : {email}')
else:
    admin = User(
        id=str(uuid.uuid4()),
        email=email,
        full_name='Administrateur DNTT',
        hashed_password=get_password_hash(password),
        role='super_admin',
        is_active=True,
    )
    db.add(admin)
    db.commit()
    print(f'✅ Admin créé : {email}')
db.close()
"

# 4. Seed pilote Conakry
echo ""
echo "── 4. Seed pilote Conakry (50 candidats) ──"
python3 -c "
import logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s %(message)s')
from app.seed_pilote_conakry import run
run()
"

echo ""
echo "═══════════════════════════════════════════════"
echo "  ✅ Setup terminé — CodeRoute Guinée prêt"
echo "═══════════════════════════════════════════════"
echo ""
echo "  Connexion admin : admin@dntt.gov.gn"
echo "  Centre pilote   : centre.kaloum@dntt.gov.gn"
echo ""
