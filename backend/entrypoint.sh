#!/usr/bin/env bash
# entrypoint.sh — CodeRoute Guinée
# Lance les migrations Alembic puis démarre Gunicorn.
# Utilise ALEMBIC_DATABASE_URL (connexion directe Neon) si disponible.
set -e

echo "=== CodeRoute Guinée — Démarrage ==="

# Migrations Alembic
if [ -n "${ALEMBIC_DATABASE_URL:-}" ]; then
    echo "→ Migrations Alembic (connexion directe Neon)..."
    DATABASE_URL="$ALEMBIC_DATABASE_URL" alembic upgrade head
else
    echo "→ Migrations Alembic (DATABASE_URL)..."
    alembic upgrade head
fi

echo "→ Démarrage Gunicorn..."
exec gunicorn app.main:app -c gunicorn.conf.py
