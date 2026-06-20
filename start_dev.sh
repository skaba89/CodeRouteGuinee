#!/usr/bin/env bash
# ===========================================================
# CodeRoute Guinée — Démarrage développement en une commande
# ===========================================================
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "🇬🇳 CodeRoute Guinée — Démarrage de l'environnement de développement"
echo "=================================================================="

# Vérifier que .env existe
if [ ! -f "$SCRIPT_DIR/.env" ]; then
    echo "❌ .env manquant — copier .env.example et configurer les variables"
    exit 1
fi

# Exporter les variables d'environnement
set -a; source "$SCRIPT_DIR/.env"; set +a

# Démarrer le backend
echo ""
echo "🚀 Démarrage du backend FastAPI..."
cd "$SCRIPT_DIR/backend"
pip install -q -r requirements.txt

# Seed si première installation
if [ "${SEED_ON_START:-false}" = "true" ]; then
    echo "🌱 Chargement des données de test..."
    PYTHONPATH=. ALLOW_DEMO_SEED_NON_DEV=true python3 -m app.seed_full
fi

# Migrations
echo "📦 Application des migrations..."
PYTHONPATH=. alembic upgrade head

# Backend en arrière-plan
PYTHONPATH=. uvicorn app.main:app --host 0.0.0.0 --port "${BACKEND_PORT:-8000}" --reload &
BACKEND_PID=$!
echo "✅ Backend démarré (PID $BACKEND_PID) → http://localhost:${BACKEND_PORT:-8000}"

# Démarrer le frontend
echo ""
echo "🌐 Démarrage du frontend React..."
cd "$SCRIPT_DIR/frontend"
npm ci --silent
npm run dev &
FRONTEND_PID=$!
echo "✅ Frontend démarré (PID $FRONTEND_PID) → http://localhost:${FRONTEND_PORT:-5173}"

echo ""
echo "=================================================================="
echo "✅ CodeRoute Guinée opérationnel"
echo ""
echo "📡 API     → http://localhost:${BACKEND_PORT:-8000}/api/v1"
echo "🌐 App     → http://localhost:${FRONTEND_PORT:-5173}"
echo "📖 Docs    → http://localhost:${BACKEND_PORT:-8000}/docs (dev uniquement)"
echo ""
echo "🔑 Comptes de test:"
echo "   super_admin@coderoute.gov.gn  / CodeRoute2026!"
echo "   admin.national@coderoute.gov.gn / CodeRoute2026!"
echo "   chef.conakry@coderoute.gov.gn / CodeRoute2026!"
echo ""
echo "Ctrl+C pour arrêter tous les services"
echo "=================================================================="

# Attendre
trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit 0" INT TERM
wait
