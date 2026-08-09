# Render — preuve du SHA réellement déployé

## Objectif

La réussite d'une CI GitHub ne prouve pas à elle seule que Render exécute exactement le même commit. CodeRoute utilise donc les variables runtime natives de Render pour exposer une empreinte de déploiement non sensible dans `/health/live` et `/health/readiness`.

Le contrôle porte principalement sur :

- `runtime.git_commit` — valeur native `RENDER_GIT_COMMIT` ;
- `runtime.git_branch` — branche Render réellement déployée ;
- `runtime.git_repo_slug` — dépôt Git lié au service ;
- `runtime.render_service_name` et `runtime.render_instance_id` — identité opérationnelle de l'instance ;
- `status=ok` sur la liveness ;
- `status=ready` sur la readiness.

Aucun secret, token, credential Render ou variable applicative sensible n'est exposé.

## Déploiement après CI

`render.yaml` définit `autoDeployTrigger: checksPass` sur :

1. `coderoute-backend` ;
2. `coderoute-offsite-backup` ;
3. `coderoute-frontend`.

Render doit donc attendre la réussite des checks CI du commit avant le déploiement. Le workflow `National Code Readiness` couvre les changements `backend/**`, `frontend/**`, `ops/**` et `render.yaml`.

Le gate national exécute également les régressions transverses P10.2/PITR, P11/SOC, P12/homologation, le Go-Live Evidence Pack et les scénarios E2E du Command Center. Les anciens workflows de patch à permission `contents: write`, utilisés pendant la construction du Command Center, sont supprimés du livrable final ; seul le contrôle permanent doit rester.

Le workflow permanent `National Go-Live Command Center Contract` possède en plus un job backend `render-fingerprint-backend`. Il exécute `test_health.py` et, dès que le vérificateur est présent, `test_render_deployment_fingerprint.py`. Ce deuxième gate rend la preuve de SHA testable depuis une PR avant tout rollout Render.

## Vérification depuis GitHub — recommandée

Après la fin du déploiement Render :

1. ouvrir l'onglet **Actions** du dépôt ;
2. sélectionner **Verify Render Deployment** ;
3. choisir **Run workflow** sur `main` ;
4. conserver l'URL backend proposée ;
5. lancer le workflow.

Le workflow utilise automatiquement `${{ github.sha }}` du `main` sélectionné comme SHA attendu.

Le job échoue si :

- `/health/live` n'est pas en 2xx ou `status != ok` ;
- `/health/readiness` n'est pas en 2xx ou `status != ready` ;
- Render n'expose pas un SHA Git complet ;
- le SHA servi par Render diffère du SHA `main` ;
- le dépôt Render diffère de `skaba89/CodeRouteGuinee`.

Un artifact `render-deployment-receipt-<sha>` est conservé 90 jours et contient le reçu JSON.

## Vérification en ligne de commande

Depuis la racine du dépôt :

```bash
cd backend
export CODEROUTE_API_BASE_URL="https://coderouteguinee-backend.onrender.com"
export CODEROUTE_EXPECTED_GIT_COMMIT="$(git rev-parse origin/main)"
python scripts/verify_render_deployment.py \
  --receipt ../go-live-evidence/render-deployment-receipt.json
```

Le SHA attendu doit être un SHA Git complet de 40 caractères. Le script refuse les URLs contenant credentials, query strings ou HTTP non chiffré hors localhost.

## Lecture du reçu

Schéma : `coderoute_render_deployment_receipt_v1`.

Les principaux checks sont :

- `LIVENESS_OK` ;
- `READINESS_OK` ;
- `RENDER_GIT_COMMIT_PRESENT` ;
- `DEPLOYED_SHA_MATCH` ;
- `REPOSITORY_MATCH`.

`assessment.passed=true` signifie uniquement que **le runtime interrogé est sain et exécute le SHA attendu**. Cela ne prouve pas à lui seul le PRA, PITR, SOC, WAF, SIEM ni l'homologation DNTT.

## Ordre de recette recommandé

1. `National Code Readiness` vert sur le SHA `main` ;
2. Render déploie ce SHA après les checks ;
3. `Verify Render Deployment` vert ;
4. archiver le reçu JSON ;
5. lancer ensuite le Go-Live Evidence Pack avec les credentials d'administration nécessaires aux endpoints protégés ;
6. conserver séparément les preuves externes/institutionnelles P10.2, P11 et P12.

## Important

Ne définir manuellement aucune variable `RENDER_GIT_COMMIT`, `RENDER_GIT_BRANCH` ou `RENDER_GIT_REPO_SLUG` dans le Blueprint. Elles doivent rester fournies nativement par Render afin que l'empreinte ne puisse pas être confondue avec une valeur déclarative statique.
