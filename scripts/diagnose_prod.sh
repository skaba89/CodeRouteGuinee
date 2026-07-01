#!/usr/bin/env bash
# diagnose_prod.sh — À lancer depuis Render Shell
# Usage : bash scripts/diagnose_prod.sh

echo "════════════════════════════════════════════"
echo "  CodeRoute Guinée — Diagnostic Production"
echo "════════════════════════════════════════════"
echo ""

# 1. Variables d'environnement critiques
echo "── 1. Variables d'environnement ──"
echo -n "  DATABASE_URL       : "
if [ -n "${DATABASE_URL:-}" ]; then
    echo "✅ définie (${DATABASE_URL:0:40}...)"
else
    echo "❌ NON DÉFINIE — C'est la cause du 500 !"
fi

echo -n "  ENVIRONMENT        : "
echo "${ENVIRONMENT:-❌ NON DÉFINIE (défaut: development)}"

echo -n "  SECRET_KEY         : "
[ -n "${SECRET_KEY:-}" ] && echo "✅ définie" || echo "❌ NON DÉFINIE"

echo -n "  CORS_ORIGINS       : "
[ -n "${CORS_ORIGINS:-}" ] && echo "✅ ${CORS_ORIGINS:0:60}" || echo "❌ NON DÉFINIE"

echo ""

# 2. Test connexion DB
echo "── 2. Test connexion Neon PostgreSQL ──"
cd /app 2>/dev/null || true
if [ -n "${DATABASE_URL:-}" ]; then
    python3 -c "
import sys
try:
    import psycopg
    url = '${DATABASE_URL}'.replace('postgresql+psycopg://', 'postgresql://')
    conn = psycopg.connect(url, connect_timeout=10)
    cur = conn.execute('SELECT version()')
    row = cur.fetchone()
    print(f'  ✅ Connexion OK : {str(row[0])[:60]}')
    conn.close()
except Exception as e:
    print(f'  ❌ Connexion ÉCHOUÉE : {e}')
    sys.exit(1)
" 2>&1
else
    echo "  ⏭️  Ignoré (DATABASE_URL absente)"
fi

echo ""

# 3. État des migrations
echo "── 3. État des migrations Alembic ──"
if [ -n "${DATABASE_URL:-}" ]; then
    cd /app && ALEMBIC_DATABASE_URL="${ALEMBIC_DATABASE_URL:-$DATABASE_URL}" \
        alembic current 2>&1 | head -5
else
    echo "  ⏭️  Ignoré (DATABASE_URL absente)"
fi

echo ""

# 4. Tables en base
echo "── 4. Tables en base ──"
if [ -n "${DATABASE_URL:-}" ]; then
    python3 -c "
try:
    import psycopg
    url = '${DATABASE_URL}'.replace('postgresql+psycopg://', 'postgresql://')
    conn = psycopg.connect(url, connect_timeout=10)
    rows = conn.execute(\"SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename\").fetchall()
    tables = [r[0] for r in rows]
    print(f'  Tables présentes ({len(tables)}) : {tables[:8]}')
    critical = {'candidates', 'users', 'questions', 'exam_sessions', 'exam_centers'}
    missing = critical - set(tables)
    if missing:
        print(f'  ❌ Tables manquantes : {missing}')
        print(f'     → Lancer : alembic upgrade head')
    else:
        print('  ✅ Tables critiques présentes')
    conn.close()
except Exception as e:
    print(f'  ❌ {e}')
" 2>&1
fi

echo ""
echo "── 5. Solution recommandée ──"
if [ -z "${DATABASE_URL:-}" ]; then
    echo "  Le problème est DATABASE_URL manquante."
    echo ""
    echo "  Dans Render Dashboard → coderoute-backend → Environment → Add:"
    echo ""
    echo "  DATABASE_URL="
    echo "  postgresql+psycopg://neondb_owner:npg_yG8BsXx7VAQo@"
    echo "  ep-bold-scene-ascskyl1-pooler.eu-central-1.aws.neon.tech"
    echo "  /neondb?sslmode=require&channel_binding=require"
    echo ""
    echo "  ENVIRONMENT=production"
    echo "  SECRET_KEY=<générer avec: python3 -c \"import secrets; print(secrets.token_hex(32))\">"
    echo ""
    echo "  Puis : Manual Deploy"
fi

echo ""
echo "════════════════════════════════════════════"
