# P10.2 — PRA réel, observabilité nationale et SLO

## 1. Portée

P10.2 transforme le socle HA de P10 en une chaîne d'exploitation vérifiable :

- métriques Prometheus sans PII et à faible cardinalité ;
- SLO explicites et règles d'alerte ;
- backup PostgreSQL chiffré avant sortie de l'hôte ;
- stockage objet hors région primaire ;
- récupération du bundle avec contrôle SHA-256 ;
- restore drill depuis le bundle chiffré ;
- preuve centrale auditable des backups/restores/failovers ;
- test de perte d'instance mesurable.

Ce chantier ne modifie ni le moteur de score, ni la banque officielle, ni les réponses candidat, ni les règles de réussite.

## 2. Séparation des responsabilités

```text
                      ┌────────────────────────────┐
                      │ API CodeRoute — 2 instances│
                      │ politique + métriques      │
                      │ aucun secret S3/AES        │
                      └──────────────┬─────────────┘
                                     │ preuves M2M
                                     │
 ┌────────────────────────────┐      │      ┌─────────────────────────┐
 │ Cron backup Render         │──────┘      │ Prometheus / Alerting   │
 │ DB backup credential       │             │ METRICS_TOKEN seulement │
 │ clé AES-256                │             └─────────────────────────┘
 │ credentials S3             │
 └──────────────┬─────────────┘
                │ bundle CRGBAK2 chiffré
                ▼
       ┌────────────────────┐
       │ Object storage     │
       │ région secondaire  │
       └────────────────────┘
```

Principe : une compromission du service web ne doit pas fournir la clé de déchiffrement des sauvegardes ni les credentials du stockage objet.

## 3. SLO techniques

Valeurs initiales P10.2 :

| Indicateur | Cible |
|---|---:|
| Disponibilité API | 99,9 % |
| Latence HTTP p95 | ≤ 1 000 ms |
| Réponses HTTP 5xx | ≤ 1 % |
| RPO cible PostgreSQL | ≤ 5 min via PITR fournisseur |
| RTO cible incident DB/région | ≤ 30 min |

Les deux derniers objectifs ne sont pas garantis par le dump quotidien. Le RPO ≤ 5 min dépend d'un PITR PostgreSQL réellement activé et testé chez le fournisseur.

## 4. Métriques Prometheus

Endpoint :

```text
GET /internal/metrics
```

Il est :

- absent de l'OpenAPI ;
- masqué par 404 si `METRICS_ENABLED=false` ;
- protégé par `Authorization: Bearer <METRICS_TOKEN>` ;
- non caché ;
- exclu du rate limiting public ;
- compatible avec plusieurs workers Gunicorn.

### 4.1 Multiprocess Gunicorn

En production :

```text
PROMETHEUS_MULTIPROC_DIR=/tmp/coderoute-prometheus
```

Le répertoire est supprimé et recréé avant chaque lancement Gunicorn. `child_exit` marque les workers morts afin d'éviter l'accumulation des gauges `live*`.

Le scrape construit un nouveau `CollectorRegistry` et un `MultiProcessCollector` à chaque requête.

### 4.2 Métriques exportées

```text
coderoute_http_requests_total
coderoute_http_request_duration_seconds
coderoute_http_inflight_requests
coderoute_readiness_component_state
coderoute_reliability_evidence_last_success_timestamp_seconds
```

### 4.3 Politique de labels

Autorisé :

```text
method
route template
a status class 2xx/3xx/4xx/5xx
readiness component
evidence kind
```

Interdit :

```text
candidate_id
attempt_id
booking_id
email
phone
identity number
raw URL
query string
answer
question content
device token
JWT
IP address
```

Une route dynamique est exportée sous sa forme template :

```text
/api/v1/exams/{attempt_id}/status
```

et jamais sous :

```text
/api/v1/exams/7e2c.../status
```

## 5. Règles Prometheus

Fichier :

```text
ops/prometheus/coderoute.rules.yml
```

Alertes principales :

- `CodeRouteApiAvailabilityBelowSLO` ;
- `CodeRouteApiHigh5xxRate` ;
- `CodeRouteApiP95LatencyHigh` ;
- `CodeRouteCriticalReadinessFailure` ;
- `CodeRouteSharedStateDegraded` ;
- `CodeRouteBackupEvidenceMissingOrStale` ;
- `CodeRouteRestoreDrillStale` ;
- `CodeRouteFailoverEvidenceStale`.

Les seuils d'alerte correspondent aux SLO initiaux. Toute modification doit passer par revue d'exploitation, pas par changement manuel dans Prometheus.

## 6. Preuve centrale d'exploitation

Endpoint machine :

```text
POST /api/v1/operations/reliability/evidence
```

Authentification :

```text
X-Reliability-Evidence-Token
```

Le secret est distinct du JWT admin et du secret metrics.

Types de preuve acceptés :

```text
backup_uploaded
restore_drill_passed
ha_failover_probe_passed
```

Le backend enregistre ces preuves dans `audit_logs` avec `actor_id=NULL`, action dédiée et métadonnées bornées.

Sont refusés dans une référence : URL, credentials ou valeur contenant `@`.

Une avance d'horloge maximale de 5 minutes est tolérée pour absorber une petite dérive de l'hôte. Au-delà, la preuve est rejetée.

## 7. Backup hors région

### 7.1 Orchestrateur

```bash
./scripts/run_offsite_backup.sh
```

Séquence :

```text
pg_dump + manifest
       │
       ▼
validation SHA/size
       │
       ▼
AES-256-GCM CRGBAK2
       │
       ├── suppression immédiate dump clair + manifest clair
       │
       ▼
upload objet hors région
       │
       ▼
HEAD : taille + metadata SHA
       │
       ▼
preuve backup_uploaded vers API centrale
       │
       ▼
nettoyage dossier temporaire
```

Le `trap` supprime le dossier temporaire sur succès, erreur ou interruption.

### 7.2 Format CRGBAK2

Le bundle utilise :

```text
AES-256-GCM
nonce 96 bits
header JSON authentifié comme AAD
streaming 1 MiB
GCM tag 128 bits
```

Le header contient uniquement :

- type et version ;
- algorithme ;
- timestamp ;
- `key_id` ;
- SHA/size du dump ;
- SHA du manifest.

Il ne contient pas la clé AES.

Une altération du header ou du ciphertext entraîne un échec d'authentification GCM avant publication du dump restauré.

## 8. Stockage objet

Le script :

```bash
python3 scripts/upload_backup_s3.py <bundle.crgbak> --receipt <receipt.json>
```

fonctionne avec une API S3-compatible.

Règles :

- HTTPS obligatoire hors laboratoire explicite ;
- credentials interdits dans l'URL endpoint ;
- région cible obligatoire ;
- région cible différente de `BACKUP_PRIMARY_REGION` si la règle hors région est active ;
- metadata SHA-256 sur l'objet ;
- `HEAD` après upload pour vérifier taille et SHA ;
- SSE S3/KMS optionnel en plus du chiffrement applicatif AES-GCM.

Le chiffrement côté objet ne remplace pas le chiffrement applicatif : le bundle est déjà chiffré avant upload.

## 9. Moindre privilège des secrets

### API web

Peut posséder :

```text
METRICS_TOKEN
RELIABILITY_EVIDENCE_TOKEN
BACKUP_S3_BUCKET         # politique, non credential
BACKUP_TARGET_REGION     # politique
BACKUP_ENCRYPTION_KEY_ID # identifiant, pas la clé
```

Ne doit jamais posséder :

```text
BACKUP_ENCRYPTION_KEY_B64
AWS_ACCESS_KEY_ID
AWS_SECRET_ACCESS_KEY
BACKUP_DATABASE_URL
```

### Cron backup

Possède uniquement les secrets nécessaires au job :

```text
BACKUP_DATABASE_URL
BACKUP_ENCRYPTION_KEY_B64
AWS_ACCESS_KEY_ID
AWS_SECRET_ACCESS_KEY
```

Le token de preuve est copié depuis le service backend par référence Blueprint.

## 10. Planification du backup

Le Blueprint configure :

```text
coderoute-offsite-backup
schedule = 30 1 * * *
```

soit un backup logique quotidien à 01:30 UTC.

Le backup logique quotidien est une défense complémentaire. Il ne remplace pas le PITR à fréquence fine.

Le cron est mono-exécution : deux backups du même service ne doivent pas tourner simultanément.

## 11. Récupération d'un backup

```bash
python3 scripts/download_backup_s3.py \
  coderoute/production/2026/08/coderoute-....crgbak \
  /secure/path/coderoute.crgbak
```

Le script :

1. fait un `HEAD` ;
2. exige `kind=coderoute-secure-backup-v2` ;
3. exige un SHA-256 valide ;
4. télécharge vers un fichier temporaire ;
5. compare taille + SHA ;
6. publie atomiquement le fichier local avec mode `0600`.

## 12. Restore drill depuis le bundle chiffré

Préconditions :

```text
BACKUP_ENCRYPTION_KEY_B64
BACKUP_ENCRYPTION_KEY_ID
RESTORE_DATABASE_URL
ALLOW_DESTRUCTIVE_RESTORE_DRILL=true
```

Puis :

```bash
RESTORE_RECEIPT_PATH=/secure/receipts/restore.json \
./scripts/secure_restore_drill.sh /secure/path/coderoute.crgbak
```

Le wrapper :

1. crée un dossier temporaire `0700` ;
2. authentifie/déchiffre le bundle ;
3. vérifie SHA/size/manifest ;
4. appelle le garde P10 de restauration ;
5. vérifie les tables critiques et Alembic ;
6. écrit un reçu ;
7. supprime tous les fichiers clairs temporaires.

### Protection production

La base cible est comparée aux bases protégées par identité :

```text
hostname canonique + port + nom de base
```

Les différences de user, mot de passe, driver ou query string ne permettent pas de contourner le garde.

## 13. Publication du restore drill

Après réussite :

```bash
python3 scripts/publish_reliability_evidence.py /secure/receipts/restore.json
```

Le prochain scrape Prometheus reconstruit également les timestamps de preuves depuis `audit_logs`, donc un redémarrage API ne fait pas disparaître l'historique d'exploitation.

## 14. Test de failover API

La sonde ne stoppe aucune instance par elle-même : la coupure est provoquée par l'orchestrateur ou un opérateur autorisé.

Lancer :

```bash
python3 scripts/ha_failover_probe.py \
  https://api.example.gov.gn \
  --duration-seconds 120 \
  --interval-seconds 0.5 \
  --min-availability 99 \
  --max-consecutive-failures 2 \
  --receipt failover.json
```

Pendant la fenêtre :

1. vérifier que deux instances sont actives ;
2. retirer/redémarrer une instance ;
3. maintenir la sonde ;
4. remettre l'instance ;
5. vérifier le reçu.

Le reçu contient :

- disponibilité observée ;
- nombre de succès/échecs ;
- latence p95 ;
- plus longue série d'échecs ;
- seuils ;
- résultat `passed`.

Publier ensuite le reçu avec `publish_reliability_evidence.py`.

## 15. Rotation de clé backup

Chaque bundle contient un `key_id`, jamais la clé.

Procédure :

1. générer une nouvelle clé AES-256 aléatoire ;
2. attribuer un nouvel identifiant, ex. `backup-key-2026-09` ;
3. déployer la nouvelle clé uniquement sur le cron backup et sur le coffre de restauration ;
4. conserver l'ancienne clé hors ligne tant qu'un backup utilisant cet identifiant est encore retenu ;
5. réaliser un backup ;
6. télécharger ce backup ;
7. effectuer un restore drill ;
8. seulement après preuve verte, considérer la rotation opérationnelle.

Ne jamais stocker la clé dans :

- le bucket ;
- le manifest ;
- Git ;
- les logs ;
- une preuve AuditLog.

## 16. Réponse aux alertes

### `CodeRouteCriticalReadinessFailure`

1. identifier le composant `configuration/database/schema/migrations` ;
2. retirer tout changement manuel non contrôlé ;
3. vérifier le pre-deploy ;
4. restaurer la DB si nécessaire ;
5. ne remettre le trafic que lorsque readiness est verte.

### `CodeRouteSharedStateDegraded`

Redis/Valkey est reconstructible :

1. confirmer que les API continuent via fallback local ;
2. restaurer le shared state ;
3. vérifier le retour à `1` ;
4. analyser l'écart temporaire de rate-limit entre instances.

### `CodeRouteBackupEvidenceMissingOrStale`

1. vérifier l'historique du cron ;
2. vérifier S3/object storage ;
3. déclencher un backup manuel ;
4. confirmer le reçu hors région ;
5. confirmer la preuve dans `/api/v1/operations/reliability`.

### `CodeRouteRestoreDrillStale`

Un backup non restauré régulièrement n'est pas considéré comme une preuve suffisante. Déclencher un drill sur base jetable et archiver le reçu.

## 17. PITR fournisseur

P10.2 n'invente pas une capacité PITR applicative. L'homologation doit obtenir une preuve fournisseur de :

- PITR actif ;
- fréquence réelle du WAL / snapshots ;
- rétention ;
- chiffrement ;
- procédure de restauration à un timestamp ;
- dernier test réussi ;
- temps réel observé ;
- responsabilités fournisseur/DNTT.

## 18. Critères pour considérer P10.2 opérationnel

Tous les points suivants doivent être prouvés :

1. `P10.2 Reliability PR CI` verte ;
2. 2 instances API réellement actives ;
3. scrape Prometheus authentifié ;
4. aucun identifiant candidat dans les labels ;
5. règles d'alerte chargées ;
6. bucket objet secondaire provisionné ;
7. clé AES présente uniquement dans le cron/coffre ;
8. premier cron `backup_uploaded` réussi ;
9. récupération du bundle réussie ;
10. restore drill réussi sur une base jetable ;
11. preuve `restore_drill_passed` visible ;
12. failover d'une instance testé ;
13. preuve `ha_failover_probe_passed` visible ;
14. PITR fournisseur démontré séparément.

## 19. Ce qui reste après P10.2

Le chantier suivant pourra traiter :

- hébergement réel Prometheus/Grafana/Alertmanager ;
- export logs vers SIEM ;
- WAF/DDoS institutionnel ;
- traces OpenTelemetry distribuées ;
- tests de charge nationaux ;
- chaos tests DB/région ;
- multi-région actif/passif ou actif/actif selon coût/SLA ;
- astreinte et matrice d'escalade ;
- exercices PCA/PRA avec la DNTT ;
- homologation sécurité formelle.
