#!/usr/bin/env bash
# Configure la copie chiffrée des sauvegardes CodeRoute vers Backblaze B2.
# Réutilise le compte B2 « distant » d'Academy s'il existe, mais avec un
# dossier et des clés de chiffrement PROPRES à CodeRoute.
# Usage : sudo ./deploy/vps/scripts/configurer-sauvegarde-b2.sh
set -euo pipefail
[ "$(id -u)" -eq 0 ] || { echo "Lancer avec sudo."; exit 1; }

read -rp "Nom du bucket B2 : " BUCKET
[ -n "$BUCKET" ] || { echo "Champ vide, abandon."; exit 1; }
if ! rclone listremotes 2>/dev/null | grep -qx "distant:"; then
  read -rp "keyID de la clé d'application : " KEY_ID
  read -rsp "applicationKey (ne s'affiche pas) : " APP_KEY; echo
  [ -n "$KEY_ID" ] && [ -n "$APP_KEY" ] || { echo "Champ vide, abandon."; exit 1; }
  mkdir -p /root/.config/rclone && chmod 700 /root/.config/rclone
  rclone config create distant b2 account="$KEY_ID" key="$APP_KEY" hard_delete=true \
    --non-interactive >/dev/null
fi

CRYPT_PW="$(openssl rand -hex 32)"; CRYPT_SALT="$(openssl rand -hex 32)"
rclone config create coderoute-crypt crypt remote="distant:${BUCKET}/coderoute" \
  password="$CRYPT_PW" password2="$CRYPT_SALT" --obscure --non-interactive >/dev/null
chmod 600 /root/.config/rclone/rclone.conf

umask 077
cat > /root/CLES-SAUVEGARDE-CODEROUTE-A-CONSERVER.txt <<TXT
Clés de chiffrement des sauvegardes distantes CodeRoute (rclone crypt).
SANS CES DEUX VALEURS, LES SAUVEGARDES DISTANTES SONT ILLISIBLES.
À recopier hors du VPS (gestionnaire de mots de passe).

Stockage    : Backblaze B2 / bucket ${BUCKET} / dossier coderoute
password    : ${CRYPT_PW}
password2   : ${CRYPT_SALT}
TXT

if rclone lsd "distant:${BUCKET}" >/dev/null 2>&1; then
  echo "-> Connexion à Backblaze OK."
else
  echo "-> ÉCHEC de connexion à Backblaze : vérifier le nom du bucket et la clé."; exit 1
fi
echo "-> Clés de chiffrement : sudo cat /root/CLES-SAUVEGARDE-CODEROUTE-A-CONSERVER.txt"
