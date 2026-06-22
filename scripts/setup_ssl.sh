#!/bin/bash
# setup_ssl.sh — Configuration SSL avec Let's Encrypt pour CodeRoute Guinée
#
# Usage :
#   sudo bash scripts/setup_ssl.sh
#
# Prérequis :
#   - Docker Compose lancé (nginx doit être UP sur le port 80)
#   - DNS api.coderoute.gov.gn et coderoute.gov.gn pointant sur ce serveur
#   - Email valide pour les notifications Let's Encrypt
#
# Ce script :
#   1. Installe certbot si absent
#   2. Obtient les certificats Let's Encrypt
#   3. Les place dans nginx/certs/
#   4. Configure le renouvellement automatique (cron)
#   5. Recharge Nginx

set -euo pipefail

# ── Configuration ──────────────────────────────────────────────────────────
DOMAINS=("api.coderoute.gov.gn" "coderoute.gov.gn" "admin.coderoute.gov.gn")
EMAIL="admin@coderoute.gov.gn"
CERTS_DIR="$(cd "$(dirname "$0")/.." && pwd)/nginx/certs"
WEBROOT_DIR="/tmp/certbot-webroot"

# Couleurs
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
info()    { echo -e "${GREEN}[INFO]${NC}  $*"; }
warn()    { echo -e "${YELLOW}[WARN]${NC}  $*"; }
error()   { echo -e "${RED}[ERROR]${NC} $*" >&2; exit 1; }

# ── Vérifications ───────────────────────────────────────────────────────────
info "Vérification des prérequis..."
[[ $EUID -ne 0 ]] && error "Ce script doit être exécuté en tant que root (sudo)"
command -v docker &>/dev/null || error "Docker non trouvé"
command -v docker-compose &>/dev/null || command -v docker &>/dev/null || error "Docker Compose non trouvé"

# Vérifier que Nginx est UP
docker compose ps nginx 2>/dev/null | grep -q "Up" || warn "Nginx semble arrêté — assurez-vous que 'docker compose up nginx' est lancé"

# ── Installation certbot ────────────────────────────────────────────────────
if ! command -v certbot &>/dev/null; then
    info "Installation de certbot..."
    if command -v apt-get &>/dev/null; then
        apt-get update -qq && apt-get install -y -qq certbot
    elif command -v yum &>/dev/null; then
        yum install -y certbot
    else
        error "Gestionnaire de paquets non supporté. Installez certbot manuellement."
    fi
fi
info "certbot $(certbot --version 2>&1 | head -1) disponible"

# ── Création répertoire webroot ─────────────────────────────────────────────
mkdir -p "$WEBROOT_DIR" "$CERTS_DIR"

# ── Obtention des certificats ───────────────────────────────────────────────
DOMAIN_ARGS=""
for domain in "${DOMAINS[@]}"; do
    DOMAIN_ARGS="$DOMAIN_ARGS -d $domain"
done

info "Obtention des certificats Let's Encrypt pour : ${DOMAINS[*]}"
info "Mode webroot — Nginx doit servir /.well-known/acme-challenge/"

# Ajouter la config webroot dans Nginx si pas déjà présente
# (le nginx.prod.conf doit avoir un bloc location /.well-known/)
certbot certonly \
    --webroot \
    --webroot-path "$WEBROOT_DIR" \
    $DOMAIN_ARGS \
    --email "$EMAIL" \
    --agree-tos \
    --non-interactive \
    --expand \
    --keep-until-expiring

# ── Copie des certificats vers nginx/certs/ ─────────────────────────────────
CERT_PATH="/etc/letsencrypt/live/${DOMAINS[0]}"
if [[ -d "$CERT_PATH" ]]; then
    cp -L "$CERT_PATH/fullchain.pem" "$CERTS_DIR/fullchain.pem"
    cp -L "$CERT_PATH/privkey.pem"   "$CERTS_DIR/privkey.pem"
    chmod 644 "$CERTS_DIR/fullchain.pem"
    chmod 600 "$CERTS_DIR/privkey.pem"
    info "✅ Certificats copiés dans $CERTS_DIR"
else
    error "Certificats non trouvés dans $CERT_PATH"
fi

# ── Rechargement Nginx ──────────────────────────────────────────────────────
info "Rechargement Nginx..."
docker compose exec nginx nginx -s reload 2>/dev/null || warn "Nginx reload échoué — redémarrage..."
docker compose restart nginx 2>/dev/null || warn "Restart Nginx échoué"
info "✅ Nginx rechargé avec les nouveaux certificats"

# ── Renouvellement automatique ──────────────────────────────────────────────
RENEW_SCRIPT="/etc/cron.d/certbot-coderoute"
cat > "$RENEW_SCRIPT" << 'CRON'
# Renouvellement Let's Encrypt — CodeRoute Guinée
# Tous les jours à 3h et 15h UTC
0 3,15 * * * root certbot renew --quiet --post-hook "cd /opt/coderoute && docker compose exec nginx nginx -s reload" >> /var/log/certbot-renew.log 2>&1
CRON
chmod 0644 "$RENEW_SCRIPT"
info "✅ Renouvellement automatique configuré (cron : 03h00 et 15h00 UTC)"

# ── Résumé ──────────────────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}  ✅ SSL configuré avec succès !${NC}"
echo -e "${GREEN}════════════════════════════════════════════════════${NC}"
echo ""
echo "  Certificats : $CERTS_DIR"
echo "  Expiration  : $(openssl x509 -enddate -noout -in "$CERTS_DIR/fullchain.pem" 2>/dev/null | cut -d= -f2 || echo 'N/A')"
echo "  Renouvellement : automatique (cron)"
echo ""
echo "  URLs sécurisées :"
for domain in "${DOMAINS[@]}"; do
    echo "    https://$domain"
done
echo ""
