# P10 — Haute disponibilité, PRA/PCA et exploitation nationale

## 1. Objectif

P10 rend le backend CodeRoute Guinée compatible avec une exploitation multi-instance et introduit une procédure de reprise testable.

Ce chantier ne modifie ni le moteur de score, ni la banque de questions, ni les règles de l'examen officiel.

P10 distingue trois niveaux :

1. **liveness** : le processus API est vivant ;
2. **readiness** : l'instance peut réellement recevoir du trafic ;
3. **PRA/PCA** : les données et le service peuvent être restaurés après incident majeur.

## 2. Architecture cible du premier incrément

```text
                    Internet
                       |
                Load Balancer Render
                  /             \
             API instance A   API instance B
             2 workers        2 workers
                  \             /
                   \           /
                  PostgreSQL / Neon
                         |
                  source de vérité

             API A ----------- API B
                  \           /
                   Redis / Valkey
              cache + rate limit
```

Redis/Valkey n'est **pas** une source de vérité pour les examens.

Il ne contient que :

- cache HTTP public tolérant à la perte ;
- compteurs de rate limiting.

Les réponses candidat, traces, résultats, paiements, réservations et audits restent dans PostgreSQL ou dans les journaux Center Edge prévus par les phases précédentes.

## 3. Scaling API

Le Blueprint P10 demande :

```yaml
numInstances: 2
```

et fixe :

```text
WEB_CONCURRENCY=2
```

Le budget de processus est donc prévisible :

```text
2 instances × 2 workers = 4 workers API
```

Toute augmentation doit être précédée d'un test de charge et d'un contrôle du budget de connexions PostgreSQL.

Le nombre de workers ne doit jamais être dérivé aveuglément du nombre de CPU visibles sur l'hôte conteneur en production nationale.

## 4. Liveness et readiness

### 4.1 Liveness

```text
GET /health
GET /health/live
```

Ne teste aucune dépendance distante.

Objectif : répondre uniquement à la question :

> Le processus Python/FastAPI est-il vivant ?

Une panne Redis ou PostgreSQL ne doit pas provoquer le redémarrage en boucle d'un processus sain.

### 4.2 Readiness

```text
GET /health/readiness
```

Contrôle :

- configuration ;
- connexion PostgreSQL ;
- tables critiques ;
- version Alembic ;
- Redis/Valkey si HA_MODE ou REDIS_REQUIRED est actif.

Une dépendance obligatoire en erreur produit :

```text
HTTP 503
status = not_ready
```

Render utilise ce point de contrôle pour ne pas considérer une instance comme prête à recevoir le trafic.

Les warnings de développement/test ne rendent pas la readiness indisponible.

## 5. État partagé Redis / Valkey

Variables :

```text
REDIS_URL
REDIS_REQUIRED=true
HA_MODE=true
EXPECTED_API_INSTANCES=2
DEPLOYMENT_ID=production
```

### 5.1 Rate limiting

Le quota global n'est plus limité à la mémoire d'un worker.

Le backend utilise une fenêtre glissante Redis basée sur un sorted set et un script Lua atomique.

Ainsi :

```text
requêtes instance A + requêtes instance B = même quota
```

Si Redis devient momentanément inaccessible :

- la requête peut continuer avec un fallback local ;
- `X-RateLimit-Backend` indique `local-fallback` ;
- la readiness passe à 503 lorsque Redis est obligatoire ;
- le load balancer peut retirer l'instance du trafic.

Cette stratégie privilégie la continuité sans masquer l'incident HA.

### 5.2 Cache public

Le cache des GET publics utilise également Redis/Valkey.

Headers d'observation :

```text
X-Cache: HIT|MISS
X-Cache-Backend: shared|local|local-fallback
```

Les endpoints `/health*` sont explicitement exclus du cache.

Aucune réponse authentifiée n'est mise en cache.

## 6. Key Value Render

Le Blueprint crée :

```text
coderoute-shared-state
```

Paramètres :

- région `frankfurt` ;
- accès public interdit (`ipAllowList: []`) ;
- politique `allkeys-lru` ;
- persistence `off`.

Le choix `off` est volontaire : les données stockées sont reconstructibles et ne doivent pas être considérées comme des données métier durables.

`REDIS_URL` est injectée via la propriété privée `connectionString` du service Key Value.

## 7. Migrations Alembic

### 7.1 Risque supprimé

Avant P10, chaque instance pouvait lancer :

```text
alembic upgrade head
```

au démarrage et continuer même après un échec de migration.

Avec plusieurs instances, ce modèle peut créer :

- migrations concurrentes ;
- démarrage avec un schéma incomplet ;
- incohérence pendant un rolling deploy.

### 7.2 Modèle P10

Render exécute une seule étape :

```text
preDeployCommand: ./scripts/predeploy.sh
```

Le script utilise :

```bash
set -euo pipefail
alembic upgrade head
alembic current
```

Une migration échouée fait échouer le déploiement avant mise en production de la nouvelle version.

L'entrypoint production utilise :

```text
RUN_MIGRATIONS_ON_STARTUP=false
RUN_BOOTSTRAP_SEED_ON_STARTUP=false
```

Aucune instance API ne migre ou ne seed automatiquement en concurrence.

## 8. Bootstrap initial

Pour une installation totalement neuve, le bootstrap admin/seed doit être une opération contrôlée et temporaire.

Exemple :

```text
RUN_BOOTSTRAP_SEED_ON_STARTUP=true
```

uniquement pendant la procédure initiale prévue, puis retour immédiat à `false`.

En production nationale, les données de référence et la banque officielle doivent ensuite passer par leurs workflows de gouvernance dédiés, pas par un seed automatique au démarrage.

## 9. Sauvegarde logique

Script :

```text
backend/scripts/backup_postgres.sh
```

Il produit :

```text
coderoute-YYYYMMDDTHHMMSSZ.dump
coderoute-YYYYMMDDTHHMMSSZ.manifest.json
```

Le manifest contient :

- timestamp UTC ;
- format ;
- taille ;
- SHA-256 ;
- version Alembic observée.

Les credentials PostgreSQL ne sont jamais imprimés.

### Important

Le dump local doit être transféré immédiatement vers un stockage externe chiffré et versionné.

Un fichier présent uniquement dans `/tmp` ou sur l'instance Render **n'est pas une sauvegarde nationale**.

## 10. Restore drill

Script :

```text
backend/scripts/restore_drill.sh <dump> <manifest>
```

Conditions obligatoires :

```text
RESTORE_DATABASE_URL=<base jetable dédiée au drill>
ALLOW_DESTRUCTIVE_RESTORE_DRILL=true
```

Le script refuse le restore si `RESTORE_DATABASE_URL` est identique à :

- `DATABASE_URL` ;
- `ALEMBIC_DATABASE_URL` ;
- `BACKUP_DATABASE_URL`.

Avant restauration :

- checksum SHA-256 du dump ;
- type du manifest.

Après restauration :

- présence des tables critiques ;
- présence de `alembic_version` ;
- version de migration ;
- émission d'un reçu `coderoute_restore_drill_receipt_v1`.

## 11. Politique PRA recommandée

Les valeurs ci-dessous sont des **objectifs à valider contractuellement**, pas des garanties déjà obtenues par ce code.

### Cible service national

- RPO souhaité pour PostgreSQL : **≤ 5 minutes** avec PITR fournisseur ;
- RTO souhaité API : **≤ 30 minutes** pour incident majeur DB/région ;
- restore drill : **mensuel** au démarrage de l'exploitation, puis au minimum trimestriel après stabilisation ;
- sauvegarde logique chiffrée : quotidienne ;
- rétention indicative : 35 jours quotidien + archives mensuelles selon politique DNTT/ANSSI/légale.

Ces objectifs doivent être alignés avec le contrat d'hébergement, la classification des données et la DNTT.

## 12. PITR

P10 apporte les outils de dump et de restauration contrôlée, mais **n'implémente pas lui-même le PITR PostgreSQL**.

Le PITR dépend du fournisseur PostgreSQL retenu.

Avant homologation nationale, il faut obtenir une preuve de :

- PITR activé ;
- fenêtre de rétention ;
- chiffrement au repos ;
- chiffrement en transit ;
- procédure de restauration ;
- restauration testée ;
- journal d'incident ;
- responsabilités fournisseur/DNTT.

## 13. Perte Redis / Valkey

Redis/Valkey est considéré reconstructible.

Scénario :

```text
Redis perdu
  -> cache perdu
  -> quotas distribués temporairement indisponibles
  -> fallback local
  -> readiness 503 en HA
  -> aucune réponse examen perdue
  -> aucune correction modifiée
```

Aucune restauration Redis n'est nécessaire pour préserver l'intégrité fonctionnelle.

## 14. Perte d'une instance API

Avec deux instances :

```text
API A down
  -> API B continue
```

Préconditions :

- aucun filesystem local requis pour les données métier ;
- DB externe ;
- cache/rate limit partagé ;
- secrets identiques entre instances ;
- health/readiness corrects.

## 15. Perte PostgreSQL

```text
PostgreSQL indisponible
  -> readiness API = 503
  -> aucune instance ne prétend être prête
  -> Center Edge conserve les mécanismes offline déjà construits
  -> restauration/failover DB selon PRA
  -> validation d'intégrité
  -> remise en trafic
```

Le mode Edge protège les examens locaux déjà autorisés selon les leases définis dans les phases précédentes ; il ne transforme pas Redis en base métier.

## 16. Procédure de restore drill

1. Générer ou récupérer le dump chiffré approuvé.
2. Vérifier son SHA-256 avec le manifest.
3. Provisionner une base PostgreSQL **jetable**.
4. Définir `RESTORE_DATABASE_URL` vers cette base.
5. Vérifier visuellement qu'elle n'est pas la production.
6. Définir `ALLOW_DESTRUCTIVE_RESTORE_DRILL=true`.
7. Exécuter `restore_drill.sh`.
8. Archiver `restore-drill-receipt.json`.
9. Effectuer des contrôles applicatifs métier supplémentaires.
10. Détruire la base de drill selon la procédure sécurité.

## 17. Observabilité introduite

Readiness expose sans secrets :

- instance ID ;
- deployment ID ;
- mode HA ;
- nombre d'instances attendu ;
- état DB ;
- état schéma ;
- état migrations ;
- état shared state ;
- latence Redis/Valkey de la sonde.

Les réponses API peuvent également indiquer :

```text
X-RateLimit-Backend
X-Cache-Backend
X-Request-ID
X-Process-Time
```

Ces signaux sont exploitables par la supervision centrale.

## 18. Ce que P10 ne prétend pas encore fournir

Ce premier incrément ne constitue pas à lui seul un hébergement souverain national complet.

Restent notamment à contractualiser ou construire :

- PostgreSQL réellement HA avec standby/failover ou service équivalent ;
- PITR activé et testé ;
- stockage objet chiffré des backups hors région primaire ;
- réplication ou stratégie multi-région ;
- WAF/DDoS institutionnel ;
- SIEM/logs centralisés avec rétention ;
- alerting 24/7 et astreinte ;
- SLO/SLA DNTT ;
- tests de charge nationaux ;
- tests chaos/failover ;
- plan de continuité documenté avec rôles nominés ;
- classification et politique de rétention des données ;
- homologation sécurité formelle.

## 19. Critères avant passage national

P10 est techniquement prêt à quitter Draft lorsque :

1. backend tests HA/PRA verts ;
2. frontend non régressé ;
3. Blueprint validé ;
4. deux instances réellement observées ;
5. Redis/Valkey partagé réellement observé ;
6. `/health/readiness` vert sur chaque instance ;
7. migration pre-deploy testée sur une copie de prod ;
8. un restore drill complet produit un reçu vert ;
9. PITR fournisseur démontré ;
10. test de perte d'une instance réalisé sans interruption candidat visible.

La réussite de ces critères techniques ne remplace pas l'homologation DNTT/Ministère/autorité sécurité compétente.
