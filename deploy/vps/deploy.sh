#!/usr/bin/env bash
# Mise à jour de la production CodeRoute sur le VPS :
# pull → build → migrations (étape séparée) → redémarrage → site du proxy commun → contrôle.
# Usage (depuis n'importe où) : ./deploy/vps/deploy.sh
set -euo pipefail
cd "$(dirname "$0")/../.."

ENV_FILE=.env.vps
[ -f "$ENV_FILE" ] || { echo "❌ $ENV_FILE absent : lancer deploy/vps/scripts/generer-env.sh (ou copier .env.vps.example)."; exit 1; }
C="sudo docker compose --env-file $ENV_FILE -f deploy/vps/docker-compose.vps.yml"
VPS_PROXY_DIR="${VPS_PROXY_DIR:-$HOME/vps-proxy}"

DOMAIN="$(sed -n 's/^CODEROUTE_DOMAIN=//p' "$ENV_FILE" | tr -d '"'"'"' ' | tail -1)"
[[ "$DOMAIN" =~ ^[a-z0-9.-]+$ ]] || { echo "❌ CODEROUTE_DOMAIN invalide dans $ENV_FILE"; exit 1; }

# Proxy HTTPS commun du VPS (~/vps-proxy, voir son README) : seul à publier 80/443.
sudo docker network inspect edge >/dev/null 2>&1 \
  || { echo "❌ Réseau edge absent : installer d'abord le proxy commun (${VPS_PROXY_DIR})."; exit 1; }
[ -x "${VPS_PROXY_DIR}/reload.sh" ] || { echo "❌ ${VPS_PROXY_DIR}/reload.sh introuvable."; exit 1; }

git pull --ff-only

$C build --pull
$C up -d --wait postgres
$C run --rm --no-deps backend ./scripts/predeploy.sh
$C up -d --wait

# L'API doit être prête avant toute publication (contrôle interne, sans proxy).
$C exec -T backend curl -fsS -H "Host: ${DOMAIN}" http://127.0.0.1:8000/health/readiness >/dev/null \
  || { echo "❌ API non prête : voir « $C logs backend »"; exit 1; }

# Site du proxy commun : écrit, validé puis rechargé sans coupure (reload.sh).
# Si la validation échoue, l'ancien fichier est remis en place.
SITE="${VPS_PROXY_DIR}/sites/coderoute.caddy"
if [ -f "$SITE" ]; then cp "$SITE" "${SITE}.precedent"; fi
sed "s/__CODEROUTE_DOMAIN__/${DOMAIN}/g" deploy/vps/coderoute.caddy.template > "$SITE"
if ! "${VPS_PROXY_DIR}/reload.sh"; then
  if [ -f "${SITE}.precedent" ]; then mv "${SITE}.precedent" "$SITE"; else rm -f "$SITE"; fi
  "${VPS_PROXY_DIR}/reload.sh" || true
  echo "❌ Site CodeRoute refusé par le proxy : configuration précédente rétablie."
  exit 1
fi
rm -f "${SITE}.precedent"

# Cache de build : on ne garde que 7 jours (images, conteneurs et volumes intacts).
sudo docker builder prune -f --filter until=168h >/dev/null

# Contrôle de bout en bout (proxy → API) sur le vrai domaine, résolu localement.
curl -sS --retry 5 --retry-delay 3 --retry-all-errors \
  --resolve "${DOMAIN}:443:127.0.0.1" "https://${DOMAIN}/health/readiness" \
  | python3 -c 'import json,sys; d=json.load(sys.stdin); print(d["status"], d.get("blocking_checks")); sys.exit(d["status"] != "ready")'
