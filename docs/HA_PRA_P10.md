# P10 — Haute disponibilité, PRA/PCA et exploitation nationale

## 1. Objectif

P10 rend le backend CodeRoute Guinée compatible avec une exploitation multi-instance et introduit une procédure de reprise testable. Ce chantier ne modifie ni le moteur de score, ni la banque de questions, ni les règles de l'examen officiel.

P10 distingue trois niveaux :

1. **liveness** : le processus API est vivant ;
2. **readiness** : l'instance peut réellement recevoir du trafic ;
3. **PRA/PCA** : les données et le service peuvent être restaurés après incident majeur.

## 2. Architecture cible

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

Redis/Valkey n'est **pas** une source de vérité pour les examens. Il ne contient que le cache HTTP public tolérant à la perte et les compteurs de rate limiting. Les réponses candidat, traces, résultats, paiements, réservations et audits restent dans PostgreSQL ou dans les journaux Center Edge.

## 3. Scaling API

Le Blueprint P10 demande `numInstances: 2` et fixe `WEB_CONCURRENCY=2`, soit un budget prévisible de 4 workers API. Toute augmentation doit être précédée d'un test de charge et d'un contrôle du budget de connexions PostgreSQL.

## 4. Liveness et readiness

### Liveness

`GET /health` et `GET /health/live` ne testent aucune dépendance distante. Une panne Redis ou PostgreSQL ne doit pas provoquer le redémarrage en boucle d'un processus Python sain.

### Readiness

`GET /health/readiness` contrôle la configuration, la connexion PostgreSQL, les tables critiques, Alembic et Redis/Valkey lorsque `HA_MODE` ou `REDIS_REQUIRED` est actif.

Une dépendance obligatoire en erreur retourne HTTP 503 avec `status=not_ready`. Les warnings de développement/test ne bloquent pas la readiness.

## 5. État partagé Redis / Valkey

Variables :

```text
REDIS_URL
REDIS_REQUIRED=true
HA_MODE=true
EXPECTED_API_INSTANCES=2
DEPLOYMENT_ID=production
```

Le rate limiting repose sur une fenêtre glissante Redis atomique : les requêtes reçues par les différentes instances participent au même quota. Si Redis devient momentanément inaccessible, les requêtes peuvent continuer avec un fallback local, mais la readiness passe à 503 lorsque Redis est obligatoire.

Le cache des GET publics utilise également Redis/Valkey. Les réponses authentifiées et les endpoints `/health*` sont exclus du cache.

Headers d'observation :

```text
X-Cache: HIT|MISS
X-Cache-Backend: shared|local|local-fallback
X-RateLimit-Backend: shared|local|local-fallback
X-Request-ID
X-Process-Time
```

## 6. Key Value Render

Le Blueprint crée `coderoute-shared-state` en région Frankfurt, sans accès public, avec `allkeys-lru` et persistence désactivée. Ce choix est volontaire : ces données sont reconstructibles et ne constituent pas des données métier durables.

## 7. Migrations Alembic

Avant P10, chaque instance pouvait lancer `alembic upgrade head` au démarrage. En multi-instance, cela ouvre la porte aux migrations concurrentes et au démarrage avec un schéma incomplet.

P10 utilise :

```text
preDeployCommand: ./scripts/predeploy.sh
```

Le script est fail-closed :

```bash
set -euo pipefail
alembic upgrade head
alembic current
```

En production :

```text
RUN_MIGRATIONS_ON_STARTUP=false
RUN_BOOTSTRAP_SEED_ON_STARTUP=false
```

Aucune instance API ne migre ou ne seed automatiquement en concurrence.

## 8. Bootstrap initial

Pour une installation neuve, le bootstrap admin/seed reste une opération contrôlée et temporaire via `RUN_BOOTSTRAP_SEED_ON_STARTUP=true`, puis doit être immédiatement remis à `false`. Les données officielles doivent ensuite suivre les workflows de gouvernance, pas un seed automatique.

## 9. Sauvegarde logique

`backend/scripts/backup_postgres.sh` produit un dump PostgreSQL custom et un manifest JSON contenant timestamp UTC, taille, SHA-256 et version Alembic observée. Les credentials ne sont jamais imprimés.

Le dump doit être transféré vers un stockage externe chiffré et versionné. Un dump présent uniquement sur l'instance ou dans `/tmp` **n'est pas une sauvegarde nationale**.

## 10. Restore drill

`backend/scripts/restore_drill.sh <dump> <manifest>` exige :

```text
RESTORE_DATABASE_URL=<base jetable dédiée au drill>
ALLOW_DESTRUCTIVE_RESTORE_DRILL=true
```

Le script refuse le restore si la cible est identique à `DATABASE_URL`, `ALEMBIC_DATABASE_URL` ou `BACKUP_DATABASE_URL`. Il vérifie le SHA-256 avant restauration, puis contrôle les tables critiques et `alembic_version` et émet un reçu `coderoute_restore_drill_receipt_v1`.

## 11. Objectifs PRA à valider contractuellement

Les valeurs suivantes sont des **objectifs**, pas des garanties déjà obtenues par le code :

- RPO PostgreSQL souhaité : **≤ 5 minutes** avec PITR fournisseur ;
- RTO API souhaité : **≤ 30 minutes** pour incident majeur DB/région ;
- restore drill : mensuel au démarrage puis au minimum trimestriel après stabilisation ;
- sauvegarde logique chiffrée : quotidienne ;
- rétention indicative : 35 jours quotidiens + archives mensuelles selon politique DNTT/autorité compétente.

## 12. PITR

P10 apporte les outils de dump et restore drill mais **n'implémente pas lui-même le PITR PostgreSQL**. Avant homologation nationale, le fournisseur DB doit démontrer : PITR activé, fenêtre de rétention, chiffrement au repos/en transit, procédure de restauration, restauration testée et responsabilités contractuelles.

## 13. Perte Redis / Valkey

```text
Redis perdu
  -> cache perdu
  -> quotas distribués temporairement indisponibles
  -> fallback local
  -> readiness 503 en HA
  -> aucune réponse examen perdue
  -> aucune correction modifiée
```

Aucune restauration Redis n'est nécessaire pour préserver l'intégrité métier.

## 14. Perte d'une instance API

Avec deux instances, la perte d'une instance doit laisser l'autre servir le trafic, sous réserve que DB, secrets, cache/rate limit partagé et health/readiness soient corrects.

## 15. Perte PostgreSQL

```text
PostgreSQL indisponible
  -> readiness API = 503
  -> aucune instance ne prétend être prête
  -> Center Edge conserve les mécanismes offline déjà construits
  -> restauration/failover DB selon PRA
  -> contrôles d'intégrité
  -> remise en trafic
```

## 16. Procédure de restore drill

1. Récupérer le dump chiffré approuvé.
2. Vérifier son SHA-256 avec le manifest.
3. Provisionner une base PostgreSQL **jetable**.
4. Définir `RESTORE_DATABASE_URL` vers cette base.
5. Vérifier qu'elle n'est pas la production.
6. Définir `ALLOW_DESTRUCTIVE_RESTORE_DRILL=true`.
7. Exécuter `restore_drill.sh`.
8. Archiver `restore-drill-receipt.json`.
9. Effectuer des contrôles métier supplémentaires.
10. Détruire la base de drill selon la procédure sécurité.

## 17. Observabilité

Readiness expose sans secrets : instance ID, deployment ID, mode HA, nombre d'instances attendu, état DB, schéma, migrations et shared state. Ces signaux peuvent alimenter la supervision centrale.

## 18. Ce que P10 ne prétend pas encore fournir

Ce premier incrément ne constitue pas à lui seul un hébergement souverain national complet. Restent notamment à contractualiser ou construire :

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
- plan de continuité avec rôles nommés ;
- politique de classification/rétention ;
- homologation sécurité formelle.

## 19. Critères avant passage national

P10 peut quitter Draft lorsque :

1. backend tests HA/PRA verts ;
2. frontend non régressé ;
3. Blueprint validé ;
4. deux instances réellement observées ;
5. Redis/Valkey partagé réellement observé ;
6. `/health/readiness` vert sur chaque instance ;
7. migration pre-deploy testée sur une copie de production ;
8. un restore drill complet produit un reçu vert ;
9. PITR fournisseur démontré ;
10. test de perte d'une instance réalisé sans interruption candidat visible.

La réussite de ces critères techniques ne remplace pas l'homologation DNTT/Ministère/autorité sécurité compétente.
