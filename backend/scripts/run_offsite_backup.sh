#!/usr/bin/env bash
set -euo pipefail

WORKDIR="$(mktemp -d "${TMPDIR:-/tmp}/coderoute-offsite-backup.XXXXXX")"
chmod 0700 "$WORKDIR"
cleanup() {
  rm -rf "$WORKDIR"
}
trap cleanup EXIT INT TERM

# 1. Dump logique + manifest P10 dans un dossier privé éphémère.
./scripts/backup_postgres.sh "$WORKDIR" >/dev/null

mapfile -t DUMPS < <(find "$WORKDIR" -maxdepth 1 -type f -name 'coderoute-*.dump' -print)
mapfile -t MANIFESTS < <(find "$WORKDIR" -maxdepth 1 -type f -name 'coderoute-*.manifest.json' -print)
if [ "${#DUMPS[@]}" -ne 1 ] || [ "${#MANIFESTS[@]}" -ne 1 ]; then
  echo "ERROR: résultat backup ambigu — exactement un dump et un manifest requis." >&2
  exit 20
fi

DUMP="${DUMPS[0]}"
MANIFEST="${MANIFESTS[0]}"
BUNDLE="$WORKDIR/$(basename "${DUMP%.dump}").crgbak"
UPLOAD_RECEIPT="$WORKDIR/offsite-upload-receipt.json"

# 2. Chiffrement authentifié avant toute sortie de l'hôte.
python3 ./scripts/secure_backup_bundle.py pack "$DUMP" "$MANIFEST" "$BUNDLE" >/dev/null

# Le clair n'est plus nécessaire dès que le bundle GCM est construit.
rm -f -- "$DUMP" "$MANIFEST"

# 3. Upload hors région + HEAD de vérification.
python3 ./scripts/upload_backup_s3.py "$BUNDLE" --receipt "$UPLOAD_RECEIPT" >/dev/null

# 4. Preuve centrale auditable. Une panne de l'API centrale fait échouer le job :
# le backup reste néanmoins déjà stocké hors région et pourra être réconcilié.
if [ "${PUBLISH_RELIABILITY_EVIDENCE:-true}" = "true" ]; then
  python3 ./scripts/publish_reliability_evidence.py "$UPLOAD_RECEIPT" >/dev/null
fi

# 5. Export facultatif du reçu sans dump ni bundle.
if [ -n "${BACKUP_RECEIPT_OUTPUT:-}" ]; then
  install -m 0600 "$UPLOAD_RECEIPT" "$BACKUP_RECEIPT_OUTPUT"
fi

echo "CodeRoute offsite backup OK"
