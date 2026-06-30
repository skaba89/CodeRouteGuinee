#!/usr/bin/env bash
# entrypoint.sh — CodeRoute Guinée
# Lance les migrations Alembic puis démarre Gunicorn.
set -e

echo "=== CodeRoute Guinée — Démarrage ==="
echo "    Environnement : ${ENVIRONMENT:-development}"
echo "    Python        : $(python --version 2>&1)"

# Vérification DATABASE_URL
if [ -z "${DATABASE_URL:-}" ]; then
    echo "⚠️  AVERTISSEMENT : DATABASE_URL non définie."
    echo "    Le backend démarrera mais les requêtes DB échoueront (503)."
    echo "    Configurer DATABASE_URL dans Render Dashboard → Environment."
else
    echo "    DB host       : $(echo $DATABASE_URL | grep -oP 'host=\K[^&]+' || echo '(pooled)')"
fi

# Migrations Alembic (uniquement si DB disponible)
if [ -n "${DATABASE_URL:-}" ] || [ -n "${ALEMBIC_DATABASE_URL:-}" ]; then
    echo "→ Migrations Alembic..."
    if [ -n "${ALEMBIC_DATABASE_URL:-}" ]; then
        DATABASE_URL="$ALEMBIC_DATABASE_URL" alembic upgrade head && echo "✓ Migrations OK"
    else
        alembic upgrade head && echo "✓ Migrations OK"
    fi
else
    echo "→ Migrations ignorées (DATABASE_URL absente)"
fi

echo "→ Démarrage Gunicorn..."
exec gunicorn app.main:app -c gunicorn.conf.py
