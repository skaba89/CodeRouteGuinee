#!/usr/bin/env bash
set -euo pipefail

if [ "${EUID}" -ne 0 ]; then
  echo "Ce script doit être exécuté en root." >&2
  exit 2
fi

SOURCE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_DIR=/etc/coderoute-edge
STATE_DIR=/var/lib/coderoute-edge
CACHE_DIR=/var/cache/coderoute-edge
RELEASE_DIR=/opt/coderoute-edge/releases

if ! id coderoute-edge >/dev/null 2>&1; then
  useradd --system --home-dir /nonexistent --shell /usr/sbin/nologin coderoute-edge
fi

install -d -o root -g coderoute-edge -m 0750 "$CONFIG_DIR"
install -d -o coderoute-edge -g coderoute-edge -m 0700 "$STATE_DIR" "$CACHE_DIR"
install -d -o coderoute-edge -g coderoute-edge -m 0750 "$RELEASE_DIR"

install -o root -g root -m 0644 "$SOURCE_DIR/coderoute-edge.service" /etc/systemd/system/coderoute-edge.service
install -o root -g root -m 0644 "$SOURCE_DIR/coderoute-edge-updater.service" /etc/systemd/system/coderoute-edge-updater.service
install -o root -g root -m 0644 "$SOURCE_DIR/coderoute-edge-updater.timer" /etc/systemd/system/coderoute-edge-updater.timer

if [ ! -f "$CONFIG_DIR/edge.env" ]; then
  install -o root -g coderoute-edge -m 0640 "$SOURCE_DIR/edge.env.example" "$CONFIG_DIR/edge.env"
  echo "Configuration créée dans $CONFIG_DIR/edge.env. Complétez les placeholders avant de démarrer le service." >&2
fi

if [ ! -f "$CONFIG_DIR/node-private-key.pem" ]; then
  echo "Clé privée gateway absente : $CONFIG_DIR/node-private-key.pem" >&2
  echo "Copiez l'identité Edge déjà enrôlée avec mode 0600 root:coderoute-edge puis relancez." >&2
  exit 3
fi
chown root:coderoute-edge "$CONFIG_DIR/node-private-key.pem"
chmod 0640 "$CONFIG_DIR/node-private-key.pem"

systemctl daemon-reload
systemctl enable coderoute-edge.service coderoute-edge-updater.timer

echo "Units installées. Le script ne démarre volontairement pas le service tant que l'artefact P9 initial, son .venv et la configuration TLS ne sont pas validés."
