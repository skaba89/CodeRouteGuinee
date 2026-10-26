# Production CodeRoute sur le VPS OVH (depuis octobre 2026)

CodeRoute tourne sur le **même VPS qu'Academy Guinéenne**, dans son propre
projet Docker Compose (`coderoute-prod`). Render n'est plus utilisé
(`render.yaml` conservé pour mémoire, déploiement automatique désactivé).

```text
Internet ─► Caddy d'Academy (80/443, HTTPS Let's Encrypt)
              ├─ domaine Academy ─► Academy
              └─ CODEROUTE_DOMAIN ─► réseau « coderoute-edge »
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
| `coderoute.caddy.template` | Bloc de site Caddy ; `deploy.sh` génère `generated/coderoute.caddy` |
| `.env.vps.example` | Modèle de `.env.vps` (racine du dépôt, jamais commité) |
| `scripts/creer-admin.sh` | Premier super-administrateur (mot de passe saisi sans écho) |
| `scripts/configurer-sauvegarde-b2.sh` | Copie chiffrée vers Backblaze B2 : dossier et clés propres à CodeRoute |
| `scripts/sauvegarde-distante.sh` + `coderoute-offsite.cron` | Copie nocturne (3 h 30, après celle d'Academy) |

## Domaine

En attendant le domaine définitif : `coderoute.<ipv4-avec-tirets>.sslip.io`
(résolu vers le VPS, certificat HTTPS automatique). Changer de domaine :
modifier `CODEROUTE_DOMAIN` dans `.env.vps`, puis `./deploy/vps/deploy.sh`
(le frontend est reconstruit avec la nouvelle adresse).

## Première installation

1. `cp deploy/vps/.env.vps.example .env.vps && chmod 600 .env.vps`, puis
   remplir chaque secret avec `openssl rand -hex 32` (valeurs toutes différentes).
   **Sauvegarder `AUDIT_CHAIN_HMAC_KEY` hors du VPS.**
2. Raccorder le Caddy d'Academy (une seule fois, voir ci-dessous).
3. `./deploy/vps/deploy.sh` — s'arrête en erreur si `/health/readiness` n'est pas `ready`.
4. `./deploy/vps/scripts/creer-admin.sh`, puis activer la 2FA du compte.
5. Sauvegardes distantes : `sudo ./deploy/vps/scripts/configurer-sauvegarde-b2.sh`,
   puis `sudo cp deploy/vps/coderoute-offsite.cron /etc/cron.d/coderoute-offsite`.

## Raccordement au Caddy d'Academy (modification du dépôt Academy)

À faire dans `gestion-scolaire-pro`, avec validation (infra Academy) :

- `deploy/vps/Caddyfile` : ajouter en fin de fichier `import /etc/caddy/sites/*.caddy` ;
- `deploy/vps/docker-compose.vps.yml`, service `caddy` :
  - volume `${CODEROUTE_CADDY_SITES_DIR:-/home/ubuntu/CodeRouteGuinee/deploy/vps/generated}:/etc/caddy/sites:ro` ;
  - réseau externe `coderoute-edge` (déclaré `external: true`) ;
- redéployer Academy (`./deploy/vps/deploy.sh`) : Caddy est recréé une fois.

Ensuite, chaque `deploy.sh` de CodeRoute recharge Caddy (`caddy reload`,
sans coupure pour Academy). Retour arrière : retirer la ligne `import` et le
volume, redéployer Academy.

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
partagé avec Academy et Kora Finance : un VPS dédié est recommandé avant une
exploitation nationale.

## Pas encore en place

- Surveillance avec alerte e-mail (à reprendre de `gestion-scolaire-pro/deploy/vps/scripts/surveillance.py`).
- Finalisation serveur des examens expirés (lot 1, tâche cron sur ce VPS).
