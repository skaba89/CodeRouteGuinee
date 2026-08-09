# P11 — SOC & Security Operations nationales

## 1. Objectif

P11 transforme la supervision technique P10/P10.2 en capacité de sécurité exploitable par la DNTT : corrélation des incidents, traces distribuées, logs structurés privacy-safe, intégrité du journal d'audit, alertes SOC, procédures WAF/DDoS et recette de charge/chaos.

P11 ne modifie ni les règles d'examen, ni la banque de questions, ni le scoring candidat.

## 2. Principes non négociables

1. **Un collecteur/SIEM ne doit jamais bloquer un examen.** Les exports OTLP sont best-effort.
2. **Une identité citoyenne ne doit pas sortir en clair vers le SOC.** Les identifiants sont pseudonymisés par HMAC.
3. **Le journal d'audit institutionnel doit être tamper-evident.** Une altération doit être détectable.
4. **L'activation P11 est séparée de la livraison du code.** Le Blueprint garde SOC/HMAC/OTLP/WAF/SIEM désactivés par défaut.
5. **Une panne Redis reste une dégradation, pas une coupure nationale.** Le modèle P10 reste inchangé.
6. **Aucun chaos destructif n'est déclenché automatiquement par le dépôt.** Les probes observent une action opérateur contrôlée.

## 3. Architecture

```text
Utilisateurs / Centres Edge
          |
      WAF / DDoS
          |
     Load Balancer
       /       \
    API A     API B
       \       /
       PostgreSQL
          |
   audit_logs HMAC

API stdout JSON ----------> Log drain / SIEM
API traces OTLP ----------> Collector OTEL ----------> SIEM/APM
/internal/metrics --------> Prometheus -------------> Alertmanager
                                                  --> astreinte DNTT
```

Le SOC ne reçoit pas de réponses d'examen, de JWT, de mot de passe, d'email brut, d'adresse IP brute, de numéro d'identité, de `candidate_id` ou d'`attempt_id` brut.

## 4. Classification des données SOC

### Autorisé

- route FastAPI template, par exemple `/api/v1/exams/{exam_id}` ;
- méthode HTTP ;
- classe/statut HTTP ;
- durée ;
- `request_id` technique ;
- `trace_id` / `span_id` ;
- rôle non nominatif ;
- `center_id` institutionnel ;
- références HMAC `usr:*`, `cand:*`, `attempt:*`, `ip:*` ;
- version applicative ;
- environnement ;
- état des composants.

### Interdit dans les exports

- mot de passe, PIN, secret, clé API ;
- Authorization/JWT/cookies ;
- email ou téléphone en clair ;
- adresse IP en clair ;
- identité/NII/NNI ;
- `user_id`, `candidate_id`, `attempt_id`, `payment_id` bruts ;
- URL brute ou query string ;
- corps de requête ;
- réponse ou correction d'examen.

Le filtre `SOCPrivacyFilter` constitue la dernière barrière avant stdout/SIEM. Les wrappers Sentry utilisent la même politique.

## 5. Pseudonymisation SOC

Variable :

```text
SOC_PSEUDONYM_KEY=<secret stable >=32 caractères>
```

La référence est :

```text
HMAC-SHA256(key, namespace + NUL + valeur)[:20]
```

Un même utilisateur produit une référence stable dans un même namespace, mais une valeur différente entre `usr`, `cand`, `actor`, `ip`, etc.

### Rotation

Ne jamais remplacer brutalement `SOC_PSEUDONYM_KEY` si une corrélation historique SOC doit être conservée. La rotation doit être planifiée avec une fenêtre où l'ancien et le nouveau mapping sont documentés hors des logs. P11 initial ne fournit pas de keyring de pseudonymisation multi-clé.

## 6. OpenTelemetry

P11 utilise un tracer OTLP HTTP volontairement minimal au lieu d'instrumenter automatiquement toutes les bibliothèques. Cela réduit le risque de collecte de query strings ou de payloads.

Configuration après provisionnement du collector :

```text
OTEL_TRACES_ENABLED=true
OTEL_EXPORTER_OTLP_ENDPOINT=https://otel.internal.example
OTEL_EXPORTER_OTLP_HEADERS=<secret du coffre>
OTEL_SERVICE_NAME=coderoute-api
OTEL_SAMPLE_RATIO=0.05
```

Exemple de collecteur : `ops/otel/collector.example.yaml`.

L'exporter est best-effort : si le collector est indisponible, le trafic HTTP continue.

## 7. Logs et SIEM

En production les logs applicatifs sont déjà au format JSON stdout. P11 ajoute :

- pseudonymisation HMAC ;
- trace/span IDs quand un span est actif ;
- événement de sécurité normalisé ;
- `request_id` pour corrélation.

Le SIEM doit être raccordé via le mécanisme de log drain de la plateforme ou un agent d'infrastructure. Il ne faut pas ajouter des credentials SIEM dans le code.

Avant de passer `SIEM_REQUIRED=true`, prouver :

- ingestion des logs des deux instances API ;
- horodatage UTC ;
- recherche par `request_id` et `trace_id` ;
- rétention définie par la politique DNTT ;
- contrôle d'accès SOC ;
- aucune PII brute sur un échantillon contrôlé.

## 8. Audit chain HMAC

### Ancien historique

CodeRoute possédait déjà une chaîne SHA-256 optionnelle. P11 ne réécrit pas cet historique.

Lors de la première activation :

1. verrou transactionnel PostgreSQL ;
2. calcul d'une empreinte SHA-256 canonique de **tout** l'historique pré-P11, y compris anciens `seq/prev_hash/entry_hash` ;
3. création de `audit.chain_anchor` avec `coderoute_audit_legacy_anchor_v2` ;
4. l'ancre devient le premier événement HMAC P11 ;
5. les nouvelles écritures continuent en HMAC-SHA256.

### Nouvelles écritures

Un hook SQLAlchemy `before_flush` signe automatiquement chaque nouveau `AuditLog`, même si l'ancien code utilise directement `db.add(AuditLog(...))`.

PostgreSQL utilise `pg_advisory_xact_lock` pour éviter que deux instances API attribuent le même numéro de séquence.

### Activation

Provisionner d'abord :

```text
AUDIT_CHAIN_HMAC_KEY=<secret institutionnel stable >=32 caractères>
```

Puis :

```text
AUDIT_CHAIN_ENABLED=true
```

Ne jamais changer directement la clé sur une chaîne active. Sans procédure de rotation, la vérification échoue volontairement.

### Vérification

- endpoint admin : `/api/v1/operations/security/status` ;
- métrique : `coderoute_audit_chain_valid` ;
- fraîcheur : `coderoute_audit_chain_last_verify_timestamp_seconds` ;
- vérification périodique pendant un scrape authentifié, par défaut toutes les 900 secondes.

Une rupture est un incident sécurité critique.

## 9. Console SOC API

Endpoint :

```text
GET /api/v1/operations/security/status
```

Rôles : `admin`, `super_admin`.

La réponse contient uniquement :

- politique SOC non secrète ;
- intégrité de la chaîne ;
- échecs/blocages de login agrégés ;
- nombre de postes suspects ;
- nombre d'incidents centre critiques ;
- codes d'alerte.

Aucune identité citoyenne n'est renvoyée par cet endpoint.

## 10. Alertes SOC

Fichier : `ops/prometheus/security.rules.yml`.

### Critiques

- `CodeRouteSOCAuditChainInvalid` ;
- `CodeRouteSOCAuditVerificationStale` ;
- `CodeRouteSOCServerErrorBurst`.

### Warning

- `CodeRouteSOCBruteForceSignal` ;
- `CodeRouteSOCRateLimitSpike`.

Les règles d'intégrité utilisent également `absent(...)`. L'absence totale d'une métrique SOC est donc détectée et non interprétée comme un état sain.

## 11. Authentification / brute force

Signal principal :

- `auth.login_failed` ;
- `auth.login_blocked` ;
- HTTP 401/403 ;
- HTTP 429.

Procédure SOC :

1. vérifier si l'événement concerne un seul `client_ref` ou plusieurs ;
2. vérifier l'évolution du rate limit ;
3. rechercher le `request_id` / `trace_id` ;
4. vérifier les incidents de centre et postes suspects ;
5. ne jamais lever manuellement un blocage sur simple demande non authentifiée ;
6. si attaque distribuée, escalader vers le WAF/DDoS.

## 12. WAF / DDoS

P11 ne prétend pas qu'un rate limit FastAPI remplace un WAF.

Avant `WAF_REQUIRED=true`, l'infrastructure nationale doit démontrer :

- domaine public derrière un fournisseur WAF/DDoS ;
- TLS valide ;
- protection L3/L4/L7 ;
- règles OWASP applicables aux endpoints publics ;
- rate limiting en bordure ;
- règles géographiques uniquement si juridiquement et opérationnellement validées ;
- procédure de bypass d'urgence contrôlée ;
- journalisation des décisions WAF vers le SOC ;
- protection de l'origin contre un contournement direct du WAF.

### Tests minimum

- rafale HTTP bénigne contrôlée ;
- requêtes manifestement malformées ;
- dépassement du quota ;
- accès direct à l'origin ;
- vérification que `/health/live` n'est pas exposé comme mécanisme de contournement ;
- vérification qu'un faux header proxy ne permet pas d'usurper l'IP d'origine.

Ne jamais réaliser un test DDoS sur la production sans autorisation écrite du fournisseur et de la DNTT.

## 13. Incident applicatif

Pour une rafale de 5xx :

1. vérifier SLO P10.2 ;
2. comparer `/health/live` et `/health/readiness` ;
3. vérifier DB/Redis ;
4. corréler `request_id` et trace OTLP ;
5. vérifier les déploiements récents ;
6. si suspicion sécurité, conserver les logs et preuves avant rollback ;
7. le rollback ne doit pas supprimer les preuves d'audit.

## 14. Conservation des preuves

Pour un incident critique conserver :

- heure UTC début/fin ;
- commit/deployment ID ;
- alertes Prometheus ;
- traces pertinentes ;
- références HMAC ;
- `request_id` ;
- état audit chain et `head_hash` ;
- actions opérateur ;
- résultat de restauration/failover si concerné.

Ne pas exporter en pièce jointe des dumps contenant des données citoyens sans procédure dédiée.

## 15. Charge nationale

Script : `ops/load/k6-national-smoke.js`.

Par défaut il ne peut pas viser le domaine Render de production. Il faut explicitement :

```text
ALLOW_PRODUCTION_LOAD_TEST=true
```

pour retirer ce garde.

Le scénario par défaut monte progressivement jusqu'à 100 VUs et vérifie :

- erreurs <1 % ;
- p95 <1 s ;
- liveness/readiness 200.

La montée à 500/1000+ utilisateurs doit se faire sur un environnement de performance dédié avec une base et des fournisseurs non-production.

## 16. Chaos contrôlé

Script passif : `backend/scripts/chaos_dependency_probe.py`.

Il **ne coupe rien**. Un opérateur réalise la perturbation et le script observe :

- `api-instance-loss` : liveness/readiness doivent rester disponibles ;
- `redis-loss` : API disponible, fallback P10 actif ;
- `database-loss` : liveness disponible, readiness non prête.

Le chaos DB/instance/Redis doit être réalisé sur staging ou lors d'une fenêtre de maintenance explicitement approuvée.

## 17. Séquence d'activation P11

### Phase A — code dormant

Après merge :

```text
SOC_ENABLED=false
AUDIT_CHAIN_ENABLED=false
OTEL_TRACES_ENABLED=false
WAF_REQUIRED=false
SIEM_REQUIRED=false
```

Aucun comportement SOC externe n'est imposé à la production.

### Phase B — privacy + audit

1. provisionner `SOC_PSEUDONYM_KEY` ;
2. provisionner `AUDIT_CHAIN_HMAC_KEY` ;
3. sauvegarde/PITR vérifiés ;
4. passer `SOC_ENABLED=true` ;
5. passer `AUDIT_CHAIN_ENABLED=true` ;
6. redéployer ;
7. vérifier création unique de l'ancre ;
8. appeler `/operations/security/status` ;
9. vérifier `coderoute_audit_chain_valid == 1`.

### Phase C — collecte externe

1. provisionner collector privé ;
2. tester OTLP sur staging ;
3. `OTEL_TRACES_ENABLED=true` ;
4. raccorder log drain/SIEM ;
5. tester absence PII ;
6. activer règles Alertmanager ;
7. définir astreinte.

### Phase D — protection edge

1. WAF/DDoS devant le domaine ;
2. protéger l'origin ;
3. tests contrôlés ;
4. `WAF_PROVIDER=<nom>` ;
5. `WAF_REQUIRED=true` ;
6. après preuve SIEM, `SIEM_REQUIRED=true`.

## 18. Recette de sortie P11

P11 n'est considéré opérationnellement terminé que lorsque :

- [ ] CI P11 réellement verte ;
- [ ] P10.2 issue #134 terminée ;
- [ ] clés SOC/audit stockées dans le coffre ;
- [ ] ancre P11 unique créée ;
- [ ] chaîne HMAC vérifiée ;
- [ ] altération de test détectée en staging ;
- [ ] logs sans PII brute ;
- [ ] Sentry sans PII brute ;
- [ ] traces OTLP sans URL/query/body ;
- [ ] collector HA ou stratégie de reprise définie ;
- [ ] alertes SOC testées ;
- [ ] canal d'astreinte testé ;
- [ ] WAF/DDoS opérationnel et origin protégé ;
- [ ] load test staging réussi ;
- [ ] perte d'instance et perte Redis testées ;
- [ ] procédure incident signée par les responsables.

## 19. Limites P11

P11 ne fournit pas encore :

- HSM/KMS gouvernemental pour la clé d'audit ;
- keyring HMAC multi-version avec rotation transparente ;
- stockage WORM externe du head d'audit ;
- SOC 24/7 humain ;
- WAF effectivement provisionné ;
- garantie fournisseur DDoS ;
- collector OpenTelemetry hébergé ;
- SIEM hébergé ;
- test de charge national réel ;
- pentest/homologation formelle.

### Scalabilité du contrôle audit

La vérification P11 initiale recalcule la chaîne et l'ancre legacy. Avec plusieurs millions de lignes, il faudra passer à des checkpoints signés/partitionnés ou à un mécanisme WORM externe. Cette évolution appartient au chantier suivant de durcissement forensic, pas au moteur d'examen.
