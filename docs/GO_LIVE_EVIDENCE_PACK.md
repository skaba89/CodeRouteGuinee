# Go-Live Evidence Pack — CodeRoute Guinée

## Objectif

`backend/scripts/collect_go_live_evidence.py` transforme les contrôles déjà présents dans CodeRoute en un dossier de preuve reproductible pour les issues de go-live P10.2 (#134), P11 (#138) et P12 (#140).

L'outil est **strictement en lecture seule**. Il ne change ni Render, ni PostgreSQL, ni le SOC, ni une politique DNTT. Il ne ferme aucune issue et ne déclare jamais une homologation institutionnelle.

## Ce que le pack collecte

Depuis le backend déployé :

- `/health/live` : liveness, instance/runtime et `deployment_id` ;
- `/health/readiness` : configuration, DB, schéma, migrations et shared-state ;
- `/api/v1/operations/reliability` : dernière preuve backup, restore drill et failover ;
- `/api/v1/operations/security/status` : activation SOC, chaîne HMAC et signaux sécurité ;
- `/api/v1/national-governance/technical-contract` : alignement politique/runtime ;
- `/api/v1/national-governance/readiness` : blockers P12 automatisés ;
- `/api/v1/national-governance/homologation-dossiers` : accessibilité des dossiers d'homologation.

Les endpoints administratifs exigent un bearer token d'un `admin` ou `super_admin`.

## Sécurité

Ne jamais passer le token dans la ligne de commande. Le collecteur le lit uniquement depuis :

```bash
CODEROUTE_ADMIN_BEARER_TOKEN
```

Les clés contenant `token`, `secret`, `password`, `authorization`, `cookie`, `api_key`, `credential` ou `private_key` sont redacted avant écriture. Les emails sont également masqués et les query strings/fragments sont supprimés des URL présentes dans les réponses.

Le répertoire `go-live-evidence/` est ignoré par Git. Les packs contiennent de l'information opérationnelle et doivent être archivés dans la GED/coffre de preuves prévu par l'équipe, pas dans le dépôt public/partagé.

## Collecte production

Depuis un poste d'administration sécurisé :

```bash
cd backend
export CODEROUTE_API_BASE_URL="https://coderouteguinee-backend.onrender.com"
export CODEROUTE_ADMIN_BEARER_TOKEN="<token-admin-court-vivant>"
export CODEROUTE_EXPECTED_DEPLOYMENT_ID="production"

python scripts/collect_go_live_evidence.py \
  --output-dir ../go-live-evidence/production-$(date -u +%Y%m%dT%H%M%SZ) \
  --fail-on-blocker
```

Sur PowerShell :

```powershell
cd backend
$env:CODEROUTE_API_BASE_URL = "https://coderouteguinee-backend.onrender.com"
$env:CODEROUTE_ADMIN_BEARER_TOKEN = "<token-admin-court-vivant>"
$env:CODEROUTE_EXPECTED_DEPLOYMENT_ID = "production"

python scripts/collect_go_live_evidence.py `
  --output-dir "../go-live-evidence/production-$(Get-Date -AsUTC -Format yyyyMMddTHHmmssZ)" `
  --fail-on-blocker
```

Après la collecte, supprimer le token de l'environnement du shell.

## Fichiers produits

Chaque pack contient :

- `evidence.json` : snapshot complet, versionné avec `coderoute_go_live_evidence_pack_v1` ;
- `evidence.md` : synthèse lisible avec PASS/BLOCKED ;
- `SHA256SUMS` : empreinte SHA-256 des deux fichiers précédents.

Le SHA permet de prouver qu'un dossier présenté en comité est identique à celui qui a été collecté.

## Lecture des résultats

`automated_checks_passed` signifie uniquement que les contrôles automatisables observés au moment de la collecte sont satisfaits.

Le pack garde toujours `institutional_homologation_claimed=false` et rappelle les preuves externes non déductibles du logiciel :

- PITR réellement activé chez le fournisseur et RPO/RTO mesurés ;
- objet de backup réellement présent hors région et restore drill archivé ;
- SIEM/OTLP, WAF/DDoS, astreinte et exercices SOC ;
- règles officielles DNTT et référence juridique ;
- droits des contenus/médias ;
- cinq pièces du dossier P12 ;
- approbateurs identifiés et décision finale habilitée.

## Utilisation pour #134 — P10.2

Le pack peut fournir automatiquement :

- preuve liveness/readiness ;
- état DB/schéma/migrations ;
- état shared-state ;
- fraîcheur des preuves `backup_uploaded`, `restore_drill_passed`, `ha_failover_probe_passed`.

Il ne remplace pas : la console du fournisseur PostgreSQL pour PITR, le reçu S3/objet, le rapport du restore drill ni la mesure RPO/RTO.

## Utilisation pour #138 — P11

Le pack permet de vérifier après activation contrôlée :

- `SOC_ENABLED` réellement visible par le runtime ;
- `AUDIT_CHAIN_ENABLED` ;
- validité de la chaîne audit ;
- absence de signal critique au moment de la collecte.

Il ne remplace pas : la preuve de stockage des clés, l'ingestion SIEM, l'OTLP, le WAF, les tests de confidentialité, les exercices incident/chaos/charge et les signatures sécurité/exploitation.

## Utilisation pour #140 — P12

Le pack capture :

- contrat technique courant ;
- politique active et alignement runtime ;
- résultat `go_live_allowed` et blockers automatisés ;
- accessibilité des dossiers d'homologation.

Il ne remplace jamais une décision DNTT, un avis juridique ou les pièces institutionnelles réelles.

## Recette avant usage national

Le script est couvert par `backend/tests/test_go_live_evidence_pack.py` :

- refus de credentials/query string dans l'URL cible ;
- refus HTTP non chiffré hors localhost ;
- redaction secrets/emails ;
- impossibilité de déclarer une homologation ;
- blocage lorsque les endpoints authentifiés ne sont pas collectés ;
- blocage lorsque les preuves PRA sont trop anciennes.
