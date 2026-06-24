#!/bin/bash
# coderoute-cron.sh — Jobs de notification CodeRoute Guinée
# Appelé par cron ou systemd-timer
# Usage : ./coderoute-cron.sh exam_reminder_24h

set -euo pipefail

JOB="${1:-exam_reminder_24h}"
WORKDIR="/opt/coderoute/backend"
LOG_FILE="/var/log/coderoute/cron.log"

# Charger les variables d'env
if [ -f "/opt/coderoute/.env" ]; then
  export $(grep -v '^#' /opt/coderoute/.env | xargs)
fi

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Démarrage job: $JOB" >> "$LOG_FILE"

cd "$WORKDIR"
PYTHONPATH=. python -m app.scheduled_notifications --job "$JOB" \
  >> "$LOG_FILE" 2>&1

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Job $JOB terminé" >> "$LOG_FILE"
