#!/usr/bin/env bash
# ===========================================================
# CodeRoute Guinée — Démarrage développement (Linux/Mac)
# Usage : ./start_dev.sh
#         SEED_ON_START=true ./start_dev.sh
# ===========================================================
set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "🇬🇳 CodeRoute Guinée — Démarrage"
echo "================================="

if [ ! -f "$SCRIPT_DIR/.env" ]; then
    echo "❌ .env manquant — copiez .env.example et configurez les variables"
    exit 1
fi

set -a; source "$SCRIPT_DIR/.env"; set +a

# Backend
cd "$SCRIPT_DIR/backend"
pip install -q -r requirements.txt

if [ "${SEED_ON_START:-false}" = "true" ]; then
    echo "🌱 Chargement des données de test..."
    PYTHONPATH=. ALLOW_DEMO_SEED_NON_DEV=true python3 -m app.seed_full
fi

PYTHONPATH=. alembic upgrade head
PYTHONPATH=. uvicorn app.main:app --host 0.0.0.0 --port "${BACKEND_PORT:-8000}" --reload &
BACKEND_PID=$!
echo "✅ Backend → http://localhost:${BACKEND_PORT:-8000}/docs"

# Frontend
cd "$SCRIPT_DIR/frontend"
npm ci --silent
npm run dev &
FRONTEND_PID=$!
echo "✅ Frontend → http://localhost:${FRONTEND_PORT:-5173}"

echo ""
echo "🔑 Comptes : super_admin@coderoute.gov.gn / CodeRoute2026!"
echo "Ctrl+C pour arrêter"
trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit 0" INT TERM
wait
