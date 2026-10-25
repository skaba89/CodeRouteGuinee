#!/usr/bin/env bash
# Mise à jour de la production CodeRoute sur le VPS :
# pull → build → migrations (étape séparée) → redémarrage → site Caddy → contrôle.
# Usage (depuis n'importe où) : ./deploy/vps/deploy.sh
set -euo pipefail
cd "$(dirname "$0")/../.."

ENV_FILE=.env.vps
[ -f "$ENV_FILE" ] || { echo "❌ $ENV_FILE absent : copier deploy/vps/.env.vps.example vers .env.vps et le remplir."; exit 1; }
C="sudo docker compose --env-file $ENV_FILE -f deploy/vps/docker-compose.vps.yml"
CADDY_CONTAINER="${CADDY_CONTAINER:-gestion-scolaire-pro-caddy-1}"

DOMAIN="$(sed -n 's/^CODEROUTE_DOMAIN=//p' "$ENV_FILE" | tr -d '"'"'"' ' | tail -1)"
[[ "$DOMAIN" =~ ^[a-z0-9.-]+$ ]] || { echo "❌ CODEROUTE_DOMAIN invalide dans $ENV_FILE"; exit 1; }

git pull --ff-only
sudo docker network inspect coderoute-edge >/dev/null 2>&1 || sudo docker network create coderoute-edge >/dev/null

$C build --pull
$C up -d --wait postgres
$C run --rm --no-deps backend ./scripts/predeploy.sh
$C up -d --wait

# L'API doit être prête avant toute publication (contrôle interne, sans Caddy).
$C exec -T backend curl -fsS -H "Host: ${DOMAIN}" http://127.0.0.1:8000/health/readiness >/dev/null \
  || { echo "❌ API non prête : voir « $C logs backend »"; exit 1; }

# Site Caddy (lu par le Caddy d'Academy, voir README « Raccordement à Caddy »).
mkdir -p deploy/vps/generated
sed "s/__CODEROUTE_DOMAIN__/${DOMAIN}/g" deploy/vps/coderoute.caddy.template > deploy/vps/generated/coderoute.caddy
if sudo docker exec "$CADDY_CONTAINER" test -f /etc/caddy/sites/coderoute.caddy 2>/dev/null; then
  sudo docker network connect coderoute-edge "$CADDY_CONTAINER" 2>/dev/null || true
  sudo docker exec "$CADDY_CONTAINER" caddy reload --config /etc/caddy/Caddyfile
else
  echo "⚠️  Caddy n'est pas encore raccordé à CodeRoute : site non publié (voir README)."
  exit 0
fi

# Cache de build : on ne garde que 7 jours (images, conteneurs et volumes intacts).
sudo docker builder prune -f --filter until=168h >/dev/null

# Contrôle de bout en bout (Caddy → API) sur le vrai domaine, résolu localement.
curl -sS --retry 5 --retry-delay 3 --retry-all-errors \
  --resolve "${DOMAIN}:443:127.0.0.1" "https://${DOMAIN}/health/readiness" \
  | python3 -c 'import json,sys; d=json.load(sys.stdin); print(d["status"], d.get("blocking_checks")); sys.exit(d["status"] != "ready")'
