#!/usr/bin/env bash
set -euo pipefail

MIGRATE_URL="${ALEMBIC_DATABASE_URL:-${DATABASE_URL:-}}"
if [ -z "$MIGRATE_URL" ] || [[ "$MIGRATE_URL" == *"CHANGE_ME"* ]]; then
  echo "ERROR: ALEMBIC_DATABASE_URL/DATABASE_URL absent ou placeholder." >&2
  exit 2
fi

# Ne jamais afficher l'URL : elle peut contenir un mot de passe.
export DATABASE_URL="$MIGRATE_URL"

echo "CodeRoute P10 pre-deploy: alembic upgrade head"
alembic upgrade head

echo "CodeRoute P10 pre-deploy: migration state"
alembic current

echo "CodeRoute P10 pre-deploy: OK"
