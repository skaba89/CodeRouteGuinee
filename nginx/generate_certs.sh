#!/usr/bin/env bash
# ==============================================================
# Génération des certificats TLS pour CodeRoute Guinée
# ==============================================================
# Deux modes :
#   1. Let's Encrypt (production) — certbot
#   2. Auto-signé (développement/test)
# ==============================================================

set -e
CERTS_DIR="$(dirname "$0")/certs"
mkdir -p "$CERTS_DIR"

MODE="${1:-selfsigned}"
DOMAIN="${2:-coderoute.gov.gn}"
EMAIL="${3:-admin@coderoute.gov.gn}"

if [ "$MODE" = "letsencrypt" ]; then
    echo "🔐 Génération Let's Encrypt pour $DOMAIN..."
    
    if ! command -v certbot &> /dev/null; then
        echo "Installation de certbot..."
        apt-get update -q && apt-get install -y -q certbot
    fi
    
    # Certbot standalone (nécessite port 80 libre)
    certbot certonly \
        --standalone \
        --agree-tos \
        --non-interactive \
        --email "$EMAIL" \
        -d "$DOMAIN" \
        -d "api.$DOMAIN" \
        --cert-path "$CERTS_DIR/fullchain.pem" \
        --key-path "$CERTS_DIR/privkey.pem"
    
    echo "✅ Certificats Let's Encrypt générés dans $CERTS_DIR"
    echo "   Renouvellement automatique : ajouter dans cron :"
    echo "   0 3 * * * certbot renew --quiet && docker compose restart nginx"

else
    echo "🔐 Génération certificat auto-signé pour $DOMAIN (dev/test)..."
    
    openssl req -x509 -nodes -newkey rsa:2048 -days 365 \
        -keyout "$CERTS_DIR/privkey.pem" \
        -out "$CERTS_DIR/fullchain.pem" \
        -subj "/C=GN/ST=Conakry/L=Conakry/O=CodeRoute Guinee/CN=$DOMAIN" \
        -addext "subjectAltName=DNS:$DOMAIN,DNS:api.$DOMAIN,DNS:www.$DOMAIN" \
        2>/dev/null
    
    echo "✅ Certificat auto-signé généré dans $CERTS_DIR"
    echo "   ⚠️  Certificat auto-signé — les navigateurs afficheront un avertissement."
    echo "   Pour la production, utilisez : ./generate_certs.sh letsencrypt $DOMAIN $EMAIL"
fi

chmod 600 "$CERTS_DIR/privkey.pem"
chmod 644 "$CERTS_DIR/fullchain.pem"
echo ""
echo "Fichiers générés :"
ls -la "$CERTS_DIR/"
