# Production CodeRoute sur le VPS OVH (depuis octobre 2026)

CodeRoute tourne sur le VPS OVH partagé (Academy Guinéenne, Kora Finance…),
dans son propre projet Docker Compose (`coderoute-prod`). Le HTTPS est assuré
par le **proxy commun du VPS**, `~/vps-proxy` : projet Caddy indépendant de
toutes les applications, seul à publier 80/443. Render n'est plus utilisé
(`render.yaml` conservé pour mémoire, déploiement automatique désactivé).

```text
Internet ─► ~/vps-proxy (Caddy, 80/443, HTTPS Let's Encrypt)
              ├─ academy-guineenne.org, kora…, minefleet… ─► autres applications
              └─ CODEROUTE_DOMAIN ─► réseau externe « edge »
                                        ├─ /api, /health ─► coderoute-backend:8000
                                        └─ le reste      ─► coderoute-frontend:4173
                 réseau interne ─► PostgreSQL 16 + db-backup (dump quotidien)
```

**Aucun port n'est publié par CodeRoute.** Docker contourne `ufw` pour les
ports publiés : un `ports:` ouvrirait le service à Internet malgré le pare-feu
(test de régression : `backend/tests/test_compose_port_exposure.py`).

## Fichiers

| Fichier | Rôle |
|---|---|
| `docker-compose.vps.yml` | PostgreSQL, API, frontend, sauvegarde locale ; aucun port publié |
| `deploy.sh` | Mise à jour : pull → build → migrations → redémarrage → site Caddy → contrôle |
| `coderoute.caddy.template` | Site du proxy commun ; `deploy.sh` l'écrit dans `~/vps-proxy/sites/coderoute.caddy` puis recharge |
| `.env.vps.example` | Modèle de `.env.vps` (racine du dépôt, jamais commité) |
| `scripts/generer-env.sh` | Crée `.env.vps` avec des secrets aléatoires, jamais affichés (refuse d'écraser) |
| `scripts/creer-admin.sh` | Premier super-administrateur (mot de passe saisi sans écho) |
| `scripts/configurer-sauvegarde-b2.sh` | Copie chiffrée vers Backblaze B2 : dossier et clés propres à CodeRoute |
| `scripts/sauvegarde-distante.sh` + `coderoute-offsite.cron` | Copie nocturne (3 h 30, après celle d'Academy) |

## Domaine

En attendant le domaine définitif : `coderoute.<ipv4-avec-tirets>.sslip.io`
(résolu vers le VPS, certificat HTTPS automatique). Changer de domaine :
modifier `CODEROUTE_DOMAIN` dans `.env.vps`, puis `./deploy/vps/deploy.sh`
(le frontend est reconstruit avec la nouvelle adresse).

## Première installation

1. `./deploy/vps/scripts/generer-env.sh` (ou copier `.env.vps.example`).
   **Sauvegarder `AUDIT_CHAIN_HMAC_KEY` hors du VPS.**
2. Prérequis : proxy commun installé (`~/vps-proxy`, réseau `edge`).
3. `./deploy/vps/deploy.sh` — s'arrête en erreur si `/health/readiness` n'est pas `ready`.
4. `./deploy/vps/scripts/creer-admin.sh`, puis activer la 2FA du compte.
5. Sauvegardes distantes : `sudo ./deploy/vps/scripts/configurer-sauvegarde-b2.sh`,
   puis `sudo cp deploy/vps/coderoute-offsite.cron /etc/cron.d/coderoute-offsite`.

## Proxy commun (`~/vps-proxy`)

- CodeRoute rejoint le réseau externe `edge` avec les alias `coderoute-backend`
  et `coderoute-frontend` ; aucune autre application n'est touchée.
- `deploy.sh` écrit `~/vps-proxy/sites/coderoute.caddy`, puis lance
  `~/vps-proxy/reload.sh` (validation + rechargement sans coupure). Si la
  validation échoue, l'ancien fichier est remis en place.
- Autre emplacement du proxy : `VPS_PROXY_DIR=/chemin ./deploy/vps/deploy.sh`.
- Retirer CodeRoute du proxy : supprimer `~/vps-proxy/sites/coderoute.caddy`
  puis `~/vps-proxy/reload.sh`.

## Mise à jour courante

```bash
./deploy/vps/deploy.sh
```

Pas de déploiement automatique depuis GitHub : une fusion dans `main` ne
change rien en production tant que `deploy.sh` n'est pas lancé.

## Seeds et données

Production = départ à zéro. Les seeds de démonstration sont refusés
(`ENVIRONMENT=production`). Centres, candidats et banque officielle s'importent
par l'administration, après validation DNTT. La démo DNTT se fait sur la stack
locale (`scripts/demo.sh`, ports limités à `127.0.0.1`).

## Restauration

```bash
C="sudo docker compose --env-file .env.vps -f deploy/vps/docker-compose.vps.yml"
$C stop backend
# DESTRUCTIF : remplace la base courante (le dump ne contient pas de DROP).
$C exec -T postgres psql -U coderoute -d postgres -c "DROP DATABASE coderoute WITH (FORCE)" -c "CREATE DATABASE coderoute"
gunzip -c backups/postgres/daily/coderoute-AAAAMMJJ.sql.gz | $C exec -T postgres psql -U coderoute -d coderoute
$C start backend
```

Depuis B2 : `sudo rclone copy coderoute-crypt:daily/coderoute-AAAAMMJJ.sql.gz /tmp/restore/`
(remote recréé avec les clés de `/root/CLES-SAUVEGARDE-CODEROUTE-A-CONSERVER.txt`).
Essai de restauration validé le 25/10/2026 sur une base jetable (29 tables, révision 0017).

## Contrôles utiles

```bash
C="sudo docker compose --env-file .env.vps -f deploy/vps/docker-compose.vps.yml"
$C ps                                   # état et santé des services
$C logs --tail 100 backend              # journaux de l'API
sudo tail /var/log/coderoute-offsite.log
```

## Ressources

Limites mémoire : PostgreSQL 768 Mo, API 768 Mo, frontend et sauvegarde 128 Mo
chacun (~1,8 Go au total) ; 3 workers Gunicorn. Le VPS (6 vCPU, 11 Go) est
partagé avec Academy, Kora Finance et MineFleet : un VPS dédié est recommandé avant une
exploitation nationale.

## Pas encore en place

- Surveillance avec alerte e-mail (à reprendre de `gestion-scolaire-pro/deploy/vps/scripts/surveillance.py`).
- Finalisation serveur des examens expirés (lot 1, tâche cron sur ce VPS).
