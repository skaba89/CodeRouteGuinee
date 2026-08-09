#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -lt 1 ]; then
  echo "Usage: $0 <secure_bundle.crgbak>" >&2
  exit 2
fi

BUNDLE="$1"
if [ ! -f "$BUNDLE" ]; then
  echo "ERROR: bundle sécurisé introuvable." >&2
  exit 2
fi

WORKDIR="$(mktemp -d "${TMPDIR:-/tmp}/coderoute-secure-restore.XXXXXX")"
chmod 0700 "$WORKDIR"
cleanup() {
  rm -rf "$WORKDIR"
}
trap cleanup EXIT INT TERM

python3 ./scripts/secure_backup_bundle.py unpack "$BUNDLE" "$WORKDIR" >/dev/null

DUMP="$WORKDIR/coderoute-restored.dump"
MANIFEST="$WORKDIR/coderoute-restored.manifest.json"
RECEIPT="${RESTORE_RECEIPT_PATH:-$(pwd)/restore-drill-receipt.json}"

RESTORE_RECEIPT_PATH="$RECEIPT" ./scripts/restore_drill.sh "$DUMP" "$MANIFEST"
chmod 0600 "$RECEIPT"
echo "CodeRoute secure PRA restore drill OK: $RECEIPT"
