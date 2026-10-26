#!/usr/bin/env bash
# Crée .env.vps (racine du dépôt) avec des secrets aléatoires, jamais affichés.
# Refuse d'écraser un fichier existant : les secrets de production ne se
# régénèrent pas (AUDIT_CHAIN_HMAC_KEY en particulier).
# Usage : ./deploy/vps/scripts/generer-env.sh [domaine]
#   domaine par défaut : coderoute.<ipv4-avec-tirets>.sslip.io
set -euo pipefail
cd "$(dirname "$0")/../../.."
ENV_FILE=.env.vps
[ ! -e "$ENV_FILE" ] || { echo "❌ $ENV_FILE existe déjà : rien n'a été modifié."; exit 1; }

DOMAIN="${1:-}"
if [ -z "$DOMAIN" ]; then
  IPV4="$(curl -4 -fsS --max-time 5 https://ifconfig.me)"
  [[ "$IPV4" =~ ^[0-9]+(\.[0-9]+){3}$ ]] || { echo "❌ IPv4 publique introuvable : passer le domaine en argument."; exit 1; }
  DOMAIN="coderoute.${IPV4//./-}.sslip.io"
fi
[[ "$DOMAIN" =~ ^[a-z0-9.-]+$ ]] || { echo "❌ Domaine invalide : $DOMAIN"; exit 1; }

secret() { openssl rand -hex 32; }
umask 077
cat > "$ENV_FILE" <<ENV
# Production CodeRoute — généré le $(date -I) par deploy/vps/scripts/generer-env.sh.
# Ne jamais commiter ni copier ce fichier. Modèle : deploy/vps/.env.vps.example.
CODEROUTE_DOMAIN=${DOMAIN}
POSTGRES_DB=coderoute
POSTGRES_USER=coderoute
POSTGRES_PASSWORD=$(secret)
SECRET_KEY=$(secret)
CSRF_SECRET=$(secret)
ADMIN_REGISTRATION_TOKEN=$(secret)
ACCESS_TOKEN_EXPIRE_MINUTES=30
AUDIT_CHAIN_ENABLED=true
AUDIT_CHAIN_HMAC_KEY=$(secret)
WEB_CONCURRENCY=3
DB_POOL_SIZE=5
DB_MAX_OVERFLOW=5
MOBILE_MONEY_MODE=sandbox
BREVO_API_KEY=
SENTRY_DSN=
ENV
chmod 600 "$ENV_FILE"
echo "-> $ENV_FILE créé pour https://${DOMAIN} (secrets non affichés)."
echo "-> À sauvegarder HORS du VPS (sans elle, l'intégrité du journal d'audit n'est plus prouvable) :"
echo "   grep ^AUDIT_CHAIN_HMAC_KEY= $ENV_FILE"
