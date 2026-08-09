#!/usr/bin/env bash
set -euo pipefail

if [ "${EUID}" -ne 0 ]; then
  echo "Ce script doit être exécuté en root." >&2
  exit 2
fi

SOURCE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_DIR=/etc/coderoute-edge
STATE_DIR=/var/lib/coderoute-edge
STAGING_DIR=/var/lib/coderoute-edge/release-staging
CACHE_DIR=/var/cache/coderoute-edge
RELEASE_DIR=/opt/coderoute-edge/releases
TRUST_FILE="$CONFIG_DIR/release-trust.json"

if ! id coderoute-edge >/dev/null 2>&1; then
  useradd --system --home-dir /nonexistent --shell /usr/sbin/nologin coderoute-edge
fi

install -d -o root -g coderoute-edge -m 0750 "$CONFIG_DIR"
install -d -o coderoute-edge -g coderoute-edge -m 0700 "$STATE_DIR" "$STAGING_DIR" "$CACHE_DIR"
# L'arbre exécutable est volontairement non inscriptible par le daemon Edge.
install -d -o root -g root -m 0755 "$RELEASE_DIR"

install -o root -g root -m 0644 "$SOURCE_DIR/coderoute-edge.service" /etc/systemd/system/coderoute-edge.service
install -o root -g root -m 0644 "$SOURCE_DIR/coderoute-edge-updater.service" /etc/systemd/system/coderoute-edge-updater.service
install -o root -g root -m 0644 "$SOURCE_DIR/coderoute-edge-updater.timer" /etc/systemd/system/coderoute-edge-updater.timer

if [ ! -f "$CONFIG_DIR/edge.env" ]; then
  install -o root -g coderoute-edge -m 0640 "$SOURCE_DIR/edge.env.example" "$CONFIG_DIR/edge.env"
  echo "Configuration créée dans $CONFIG_DIR/edge.env. Complétez les placeholders avant de démarrer le service." >&2
fi

if [ ! -f "$CONFIG_DIR/node-private-key.pem" ]; then
  echo "Clé privée gateway absente : $CONFIG_DIR/node-private-key.pem" >&2
  echo "Copiez l'identité Edge déjà enrôlée avec mode 0640 root:coderoute-edge puis relancez." >&2
  exit 3
fi
chown root:coderoute-edge "$CONFIG_DIR/node-private-key.pem"
chmod 0640 "$CONFIG_DIR/node-private-key.pem"

if [ ! -f "$TRUST_FILE" ]; then
  echo "Trust store release absent : $TRUST_FILE" >&2
  echo "Provisionnez hors bande le JSON trusted_keys issu de la DNTT, vérifiez son fingerprint puis relancez." >&2
  exit 4
fi
chown root:root "$TRUST_FILE"
chmod 0644 "$TRUST_FILE"
python3 - <<'PY'
import json
path = '/etc/coderoute-edge/release-trust.json'
with open(path, encoding='utf-8') as handle:
    payload = json.load(handle)
keys = payload.get('trusted_keys') if isinstance(payload, dict) else None
if not isinstance(keys, list) or not keys:
    raise SystemExit('release-trust.json invalide : trusted_keys vide')
for item in keys:
    if not isinstance(item, dict) or not item.get('key_id') or not item.get('public_key_b64'):
        raise SystemExit('release-trust.json invalide : key_id/public_key_b64 obligatoire')
PY

systemctl daemon-reload
systemctl enable coderoute-edge.service coderoute-edge-updater.timer

echo "Units installées. Le script ne démarre volontairement pas le service tant que l'artefact P9 initial, son .venv et la configuration TLS ne sont pas validés."
