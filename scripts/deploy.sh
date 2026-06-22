#!/bin/bash
# deploy.sh — Déploiement production CodeRoute Guinée
#
# Usage :
#   bash scripts/deploy.sh [--skip-ssl] [--skip-seed] [--rollback]
#
# Ce script :
#   1. Vérifie les prérequis (.env, Docker)
#   2. Pull les images et rebuild si nécessaire
#   3. Lance alembic upgrade head
#   4. Relance les services en zero-downtime
#   5. Vérifie le healthcheck
#   6. Configure SSL si premier déploiement

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
COMPOSE_FILE="$PROJECT_DIR/docker-compose.prod.yml"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'
info()    { echo -e "${GREEN}[$(date '+%H:%M:%S')]${NC} $*"; }
warn()    { echo -e "${YELLOW}[WARN]${NC} $*"; }
error()   { echo -e "${RED}[ERROR]${NC} $*" >&2; exit 1; }
step()    { echo -e "\n${BLUE}═══ $* ═══${NC}"; }

SKIP_SSL=false
SKIP_SEED=false
ROLLBACK=false

for arg in "$@"; do
    case $arg in
        --skip-ssl)  SKIP_SSL=true ;;
        --skip-seed) SKIP_SEED=true ;;
        --rollback)  ROLLBACK=true ;;
    esac
done

cd "$PROJECT_DIR"

# ── 0. Rollback ────────────────────────────────────────────────────────────
if $ROLLBACK; then
    step "ROLLBACK"
    warn "Rollback vers la version précédente..."
    docker compose -f "$COMPOSE_FILE" down
    git stash
    docker compose -f "$COMPOSE_FILE" up -d
    info "✅ Rollback effectué"
    exit 0
fi

# ── 1. Prérequis ───────────────────────────────────────────────────────────
step "1. Vérification des prérequis"
[[ -f ".env" ]] || error ".env manquant — cp .env.example .env et configurer"
command -v docker &>/dev/null || error "Docker non installé"
command -v git &>/dev/null || error "Git non installé"

# Vérifier les variables critiques
source .env 2>/dev/null || true
[[ -z "${SECRET_KEY:-}" ]]   && error "SECRET_KEY non configuré dans .env"
[[ -z "${DATABASE_URL:-}" ]] && error "DATABASE_URL non configuré dans .env"
[[ "${SECRET_KEY:-}" == *"replace"* ]] && error "SECRET_KEY contient encore la valeur par défaut"

# Avertissements non bloquants
[[ -z "${BREVO_API_KEY:-}" ]]   && warn "BREVO_API_KEY absent — emails désactivés"
[[ -z "${WAVE_API_KEY:-}" ]]    && warn "WAVE_API_KEY absent — paiements Wave en sandbox"
[[ -z "${MOBILE_MONEY_MODE:-}" ]] && warn "MOBILE_MONEY_MODE non défini (défaut: sandbox)"

info "✅ Prérequis OK"

# ── 2. Git pull ────────────────────────────────────────────────────────────
step "2. Mise à jour du code"
git fetch origin main
LOCAL=$(git rev-parse HEAD)
REMOTE=$(git rev-parse origin/main)
if [[ "$LOCAL" != "$REMOTE" ]]; then
    info "Nouvelles modifications disponibles..."
    git pull origin main
    info "✅ Code mis à jour ($(git rev-parse --short HEAD))"
else
    info "✅ Code déjà à jour ($(git rev-parse --short HEAD))"
fi

# ── 3. Build ───────────────────────────────────────────────────────────────
step "3. Build des images Docker"
docker compose -f "$COMPOSE_FILE" build --pull
info "✅ Images construites"

# ── 4. Démarrage PostgreSQL ─────────────────────────────────────────────────
step "4. Démarrage PostgreSQL"
docker compose -f "$COMPOSE_FILE" up -d postgres
info "Attente PostgreSQL..."
timeout 60 bash -c 'until docker compose -f '"$COMPOSE_FILE"' exec -T postgres pg_isready -q; do sleep 2; done'
info "✅ PostgreSQL prêt"

# ── 5. Migrations Alembic ──────────────────────────────────────────────────
step "5. Migrations Alembic"
docker compose -f "$COMPOSE_FILE" run --rm backend alembic upgrade head
info "✅ Migrations appliquées"

# ── 6. Déploiement zero-downtime ───────────────────────────────────────────
step "6. Déploiement des services"
docker compose -f "$COMPOSE_FILE" up -d --remove-orphans
info "✅ Services démarrés"

# ── 7. Healthcheck ────────────────────────────────────────────────────────
step "7. Healthcheck"
info "Attente du backend (max 60s)..."
timeout 60 bash -c 'until curl -sf http://localhost:8000/health > /dev/null; do sleep 3; done' \
    && info "✅ Backend healthy" \
    || warn "Backend n'a pas répondu dans les délais — vérifier les logs"

# ── 8. Bootstrap admin (premier déploiement) ─────────────────────────────
if [[ -n "${BOOTSTRAP_ADMIN_EMAIL:-}" ]] && [[ -n "${BOOTSTRAP_ADMIN_PASSWORD:-}" ]]; then
    step "8. Bootstrap admin"
    docker compose -f "$COMPOSE_FILE" exec -T backend \
        python -m app.bootstrap_admin 2>/dev/null && info "✅ Admin bootstrappé" || warn "Bootstrap ignoré (admin déjà existant)"
fi

# ── 9. Seed données initiales ─────────────────────────────────────────────
if ! $SKIP_SEED; then
    step "9. Données initiales"
    # Vérifier si des données existent déjà
    CANDIDATE_COUNT=$(docker compose -f "$COMPOSE_FILE" exec -T postgres \
        psql -U "${POSTGRES_USER:-coderoute}" -d "${POSTGRES_DB:-coderoute}" \
        -tAc "SELECT COUNT(*) FROM candidates" 2>/dev/null || echo "0")
    if [[ "$CANDIDATE_COUNT" -eq 0 ]]; then
        info "Base vide — chargement des données initiales..."
        docker compose -f "$COMPOSE_FILE" exec -T backend \
            env ALLOW_SEED_IN_PROD=true python -m app.seed_full
        info "✅ Données initiales chargées"
    else
        info "✅ Base non vide ($CANDIDATE_COUNT candidats) — seed ignoré"
    fi
fi

# ── 10. SSL (premier déploiement) ─────────────────────────────────────────
if ! $SKIP_SSL && [[ ! -f "nginx/certs/fullchain.pem" ]]; then
    step "10. Configuration SSL"
    if command -v certbot &>/dev/null; then
        bash scripts/setup_ssl.sh
    else
        warn "certbot non trouvé — exécuter manuellement : sudo bash scripts/setup_ssl.sh"
    fi
elif ! $SKIP_SSL && [[ -f "nginx/certs/fullchain.pem" ]]; then
    info "✅ Certificats SSL déjà présents"
fi

# ── Résumé ────────────────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}  ✅ Déploiement terminé — $(git rev-parse --short HEAD)${NC}"
echo -e "${GREEN}════════════════════════════════════════════════════${NC}"
echo ""
echo "  API     : https://api.coderoute.gov.gn"
echo "  App     : https://coderoute.gov.gn"
echo "  Health  : https://api.coderoute.gov.gn/health"
echo ""
echo "  Logs    : docker compose -f docker-compose.prod.yml logs -f"
echo "  Rollback: bash scripts/deploy.sh --rollback"
echo ""
