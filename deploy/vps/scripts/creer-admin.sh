#!/usr/bin/env bash
# Crée (ou réactive) le super-administrateur de la production CodeRoute.
# Le mot de passe est saisi sans écho : il n'apparaît ni à l'écran, ni dans
# l'historique, ni dans .env.vps.
# Usage : ./deploy/vps/scripts/creer-admin.sh
set -euo pipefail
cd "$(dirname "$0")/../../.."
read -rp "E-mail du super-administrateur : " BOOTSTRAP_ADMIN_EMAIL
read -rp "Nom complet : " BOOTSTRAP_ADMIN_FULL_NAME
read -rsp "Mot de passe (12 caractères minimum, ne s'affiche pas) : " BOOTSTRAP_ADMIN_PASSWORD; echo
export BOOTSTRAP_ADMIN_EMAIL BOOTSTRAP_ADMIN_FULL_NAME BOOTSTRAP_ADMIN_PASSWORD
sudo --preserve-env=BOOTSTRAP_ADMIN_EMAIL,BOOTSTRAP_ADMIN_FULL_NAME,BOOTSTRAP_ADMIN_PASSWORD \
  docker compose --env-file .env.vps -f deploy/vps/docker-compose.vps.yml run --rm --no-deps \
  -e BOOTSTRAP_ADMIN_EMAIL -e BOOTSTRAP_ADMIN_FULL_NAME -e BOOTSTRAP_ADMIN_PASSWORD \
  backend python -m app.bootstrap_admin
echo "-> Activer ensuite la double authentification depuis le compte."
