#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════
# CodeRoute Guinée — Initialisation Neon après déploiement Render
# À exécuter UNE SEULE FOIS depuis le Shell Render ou en local
# avec les variables d'env Render configurées.
# ═══════════════════════════════════════════════════════════════════
set -euo pipefail

echo "╔══════════════════════════════════════════════════════════╗"
echo "║  CodeRoute Guinée — Init Neon + Seed                    ║"
echo "╚══════════════════════════════════════════════════════════╝"

# ── 1. Vérifier les variables requises ──────────────────────────────
required_vars=(DATABASE_URL ALEMBIC_DATABASE_URL SECRET_KEY BOOTSTRAP_ADMIN_EMAIL BOOTSTRAP_ADMIN_PASSWORD)
for var in "${required_vars[@]}"; do
    if [ -z "${!var:-}" ]; then
        echo "❌ Variable manquante : $var"
        exit 1
    fi
done
echo "✅ Variables d'environnement OK"

# ── 2. Migrations Alembic (connexion directe) ───────────────────────
echo ""
echo "📦 Application des migrations Alembic..."
# Utilise ALEMBIC_DATABASE_URL (connexion directe sans pooler)
export DATABASE_URL="$ALEMBIC_DATABASE_URL"
alembic upgrade head
echo "✅ Migrations appliquées"

# ── 3. Remettre DATABASE_URL poolée pour le seed ────────────────────
export DATABASE_URL="${DATABASE_URL_POOLER:-$DATABASE_URL}"

# ── 4. Bootstrap admin ─────────────────────────────────────────────
echo ""
echo "👤 Bootstrap administrateur..."
python3 - << 'PYEOF'
import os, sys
sys.path.insert(0, '/app')
from app.db.session import SessionLocal
from app.bootstrap_admin import bootstrap_admin

db = SessionLocal()
try:
    result = bootstrap_admin(db)
    print(f"  ✅ {result}")
except Exception as e:
    print(f"  ⚠️  {e} (peut-être déjà créé)")
finally:
    db.close()
PYEOF

# ── 5. Seed complet : 200 questions + données demo ──────────────────
echo ""
echo "🌱 Seed des données..."
python3 - << 'PYEOF'
import sys
sys.path.insert(0, '/app')
from app.db.session import SessionLocal
from app.seed_full import (
    seed_questions, seed_users, seed_centers,
    seed_sessions, seed_elearning_content
)

db = SessionLocal()
try:
    print("  → Questions (200)...")
    questions = seed_questions(db)
    print(f"  ✅ {len(questions)} questions en banque")

    print("  → Utilisateurs...")
    users = seed_users(db)
    print(f"  ✅ {len(users)} utilisateurs")

    print("  → Centres...")
    centers = seed_centers(db)
    print(f"  ✅ {len(centers)} centres")

    print("  → Sessions d'examen...")
    sessions = seed_sessions(db, centers)
    print(f"  ✅ {len(sessions)} sessions")

except Exception as e:
    print(f"  ⚠️  {e}")
finally:
    db.close()
PYEOF

echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║  ✅ Initialisation terminée !                           ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""
echo "🔗 Vérifier : curl https://\$RENDER_EXTERNAL_URL/health"
echo "📚 Docs API : https://\$RENDER_EXTERNAL_URL/docs"
