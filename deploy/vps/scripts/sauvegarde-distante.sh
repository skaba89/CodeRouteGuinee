#!/usr/bin/env bash
# Copie chiffrée des dumps PostgreSQL CodeRoute vers B2 (remote rclone
# « coderoute-crypt »), lancée chaque nuit par cron en root
# (voir deploy/vps/coderoute-offsite.cron).
set -euo pipefail
SRC="$(cd "$(dirname "$0")/../../.." && pwd)/backups/postgres"
LOG=/var/log/coderoute-offsite.log
# Tant que configurer-sauvegarde-b2.sh n'a pas créé le remote, ne rien faire.
rclone listremotes 2>/dev/null | grep -qx "coderoute-crypt:" || exit 0
{
  echo "=== $(date -Is) début"
  for d in daily weekly monthly; do
    # *-latest.* est un lien remplacé chaque jour : --immutable le refuserait.
    rclone copy "$SRC/$d" "coderoute-crypt:$d" --copy-links --immutable --exclude "*-latest.*"
  done
  # Rétention distante : 200 jours (couvre les 6 mois de dumps mensuels).
  rclone delete "coderoute-crypt:" --min-age 200d
  echo "=== $(date -Is) OK"
} >>"$LOG" 2>&1
