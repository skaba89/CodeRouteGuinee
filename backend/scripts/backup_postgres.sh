#!/usr/bin/env bash
set -euo pipefail

SOURCE_URL="${BACKUP_DATABASE_URL:-${ALEMBIC_DATABASE_URL:-${DATABASE_URL:-}}}"
if [ -z "$SOURCE_URL" ] || [[ "$SOURCE_URL" == *"CHANGE_ME"* ]]; then
  echo "ERROR: URL PostgreSQL de sauvegarde absente." >&2
  exit 2
fi

# SQLAlchemy accepte postgresql+psycopg://, libpq attend postgresql://.
PG_URL="${SOURCE_URL/postgresql+psycopg:/postgresql:}"
OUT_DIR="${1:-${BACKUP_OUTPUT_DIR:-/tmp/coderoute-backups}}"
mkdir -p "$OUT_DIR"
chmod 0700 "$OUT_DIR"

STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
DUMP="$OUT_DIR/coderoute-$STAMP.dump"
MANIFEST="$OUT_DIR/coderoute-$STAMP.manifest.json"

echo "CodeRoute PRA: création du dump PostgreSQL (credentials non affichés)"
pg_dump \
  --dbname="$PG_URL" \
  --format=custom \
  --compress=9 \
  --no-owner \
  --no-acl \
  --file="$DUMP"

SHA256="$(sha256sum "$DUMP" | awk '{print $1}')"
SIZE="$(stat -c%s "$DUMP")"
ALEMBIC_VERSION="$(psql "$PG_URL" -Atqc "SELECT version_num FROM alembic_version LIMIT 1" 2>/dev/null || true)"

DUMP="$DUMP" MANIFEST="$MANIFEST" SHA256="$SHA256" SIZE="$SIZE" ALEMBIC_VERSION="$ALEMBIC_VERSION" python3 - <<'PY'
import json
import os
from datetime import UTC, datetime
from pathlib import Path

payload = {
    "kind": "coderoute_postgres_backup_v1",
    "created_at": datetime.now(UTC).isoformat(),
    "dump_file": Path(os.environ["DUMP"]).name,
    "format": "pg_dump_custom",
    "sha256": os.environ["SHA256"],
    "size_bytes": int(os.environ["SIZE"]),
    "alembic_version": os.environ.get("ALEMBIC_VERSION") or None,
}
Path(os.environ["MANIFEST"]).write_text(
    json.dumps(payload, sort_keys=True, indent=2),
    encoding="utf-8",
)
PY
chmod 0600 "$DUMP" "$MANIFEST"
echo "CodeRoute PRA backup OK: $DUMP"
echo "Manifest: $MANIFEST"
