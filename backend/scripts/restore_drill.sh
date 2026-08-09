#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -lt 2 ]; then
  echo "Usage: $0 <dump_file> <manifest.json>" >&2
  exit 2
fi

DUMP="$1"
MANIFEST="$2"
RESTORE_URL="${RESTORE_DATABASE_URL:-}"
if [ -z "$RESTORE_URL" ] || [[ "$RESTORE_URL" == *"CHANGE_ME"* ]]; then
  echo "ERROR: RESTORE_DATABASE_URL est obligatoire et doit cibler une base jetable de recette PRA." >&2
  exit 2
fi
if [ "${ALLOW_DESTRUCTIVE_RESTORE_DRILL:-false}" != "true" ]; then
  echo "ERROR: définir ALLOW_DESTRUCTIVE_RESTORE_DRILL=true pour confirmer le restore destructif de la base de drill." >&2
  exit 3
fi

normalize_url() {
  local value="$1"
  echo "${value/postgresql+psycopg:/postgresql:}"
}
RESTORE_PG_URL="$(normalize_url "$RESTORE_URL")"

for protected in "${DATABASE_URL:-}" "${ALEMBIC_DATABASE_URL:-}" "${BACKUP_DATABASE_URL:-}"; do
  if [ -n "$protected" ] && [ "$(normalize_url "$protected")" = "$RESTORE_PG_URL" ]; then
    echo "ERROR: refus de restaurer dans une base source/production protégée." >&2
    exit 4
  fi
done

if [ ! -f "$DUMP" ] || [ ! -f "$MANIFEST" ]; then
  echo "ERROR: dump ou manifest introuvable." >&2
  exit 5
fi

EXPECTED_SHA="$(python3 - "$MANIFEST" <<'PY'
import json, sys
from pathlib import Path
payload = json.loads(Path(sys.argv[1]).read_text(encoding='utf-8'))
if payload.get('kind') != 'coderoute_postgres_backup_v1':
    raise SystemExit('manifest kind invalide')
print(payload['sha256'])
PY
)"
ACTUAL_SHA="$(sha256sum "$DUMP" | awk '{print $1}')"
if [ "$EXPECTED_SHA" != "$ACTUAL_SHA" ]; then
  echo "ERROR: checksum du dump invalide." >&2
  exit 6
fi

echo "CodeRoute PRA: restauration vers la base jetable (credentials non affichés)"
pg_restore \
  --dbname="$RESTORE_PG_URL" \
  --clean \
  --if-exists \
  --no-owner \
  --no-acl \
  "$DUMP"

RECEIPT="${RESTORE_RECEIPT_PATH:-$(dirname "$DUMP")/restore-drill-receipt.json}"
RESTORE_DATABASE_URL="$RESTORE_PG_URL" DUMP_SHA256="$ACTUAL_SHA" RECEIPT="$RECEIPT" python3 - <<'PY'
import json
import os
from datetime import UTC, datetime
from pathlib import Path

import psycopg

critical = [
    'users', 'candidates', 'centers', 'exam_sessions', 'bookings',
    'payments', 'audit_logs', 'alembic_version',
]
checks = {}
version = None
with psycopg.connect(os.environ['RESTORE_DATABASE_URL']) as conn:
    with conn.cursor() as cur:
        for table in critical:
            cur.execute("SELECT to_regclass(%s)", (f"public.{table}",))
            checks[table] = cur.fetchone()[0] is not None
        if checks.get('alembic_version'):
            cur.execute("SELECT version_num FROM alembic_version LIMIT 1")
            row = cur.fetchone()
            version = row[0] if row else None

ok = all(checks.values()) and bool(version)
payload = {
    'kind': 'coderoute_restore_drill_receipt_v1',
    'verified_at': datetime.now(UTC).isoformat(),
    'ok': ok,
    'dump_sha256': os.environ['DUMP_SHA256'],
    'critical_tables': checks,
    'alembic_version': version,
}
Path(os.environ['RECEIPT']).write_text(json.dumps(payload, sort_keys=True, indent=2), encoding='utf-8')
if not ok:
    raise SystemExit('restore drill incomplet')
PY
chmod 0600 "$RECEIPT"
echo "CodeRoute PRA restore drill OK: $RECEIPT"
