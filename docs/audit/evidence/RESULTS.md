# Résultats des contrôles — 26 octobre 2026

Base : 2b4e9b809ff27ed9111bc51c074e599e166b1793. Python 3.12.14, Node 24.22.1. Environnement Python isolé installé depuis backend/requirements.txt ; npm ci avec lockfile. Aucun service de production modifié.

| Contrôle | Résultat | Preuve |
|---|---|---|
| Inventaire et parsing AST | 861 fichiers suivis, 442 Python ; 1350 fonctions test ; 275 déclarations routes ; 17 migrations ; 20 workflows | source_inventory.json |
| pytest backend complet avec coverage | **Inachevé** : progression au-delà de 65 %, un xfail et des skips visibles ; aucun bilan ni couverture finale | pytest-incomplete.txt |
| Santé exécutée séparément | 6 passed, 2 warnings, 0.71 s | health-tests.txt |
| Ruff complet | exit 1, 210 écarts | ruff.json |
| Ruff sélection critique E9,F63,F7,F82 | exit 0, All checks passed | ruff-critical.txt |
| mypy 2.4.0, ignore-missing-imports | exit 1, 98 erreurs / 35 fichiers, 171 fichiers vérifiés | mypy.txt |
| npm ci | Réussi, 356 paquets ajoutés | Installation locale, lockfile non modifié |
| TypeScript | exit 0 | typecheck.txt |
| Build Vite/PWA | exit 0 | build.txt |
| Playwright --list | Collection disponible, 21 fichiers specs | Source et configuration inventoriées |
| Playwright exécution | **Bloqué avant test**, aucun test navigateur exécuté | playwright.json |
| Installation Chromium | Échec : archive téléchargée tronquée/invalide | browser-install.txt |
| npm audit | exit 0, 0 vulnérabilité rapportée | npm-audit.json |
| pip-audit 2.10.1 | exit 1, 66 entrées, 8 paquets, 46 couples paquet/avis distincts | pip-audit.json |
| Alembic heads | exit 0, une tête 0017 | alembic-heads.txt |
| Migrations depuis base vide SQLite + tests migration + seed jetable | exit 0 | migrations-sqlite.txt |
| PostgreSQL local | Non exécuté : aucun serveur/binaire initial, installation impossible avec permissions disponibles | Aucune preuve locale revendiquée |
| pytest Edge, PYTHONPATH=edge_agent | exit 1, 41 passed, 3 failed, 0.54 s | edge-tests.txt |
| Reproductions PAY-01 / SEC-01 / SEC-02 | Anomalies confirmées sans appel réseau ni base réelle | reproductions.json |
| Runtime Render via dernier workflow consulté | Liveness 200 ; readiness 503 ; SHA antérieur au HEAD | github-runtime-check.json |

Les sorties texte sont normalisées uniquement pour les espaces de fin de ligne.

## Commandes

Depuis backend/, avec environnement jetable :

```bash
PYTHONPATH=. DATABASE_URL=sqlite+pysqlite:///:memory: AUTO_CREATE_TABLES=true ENVIRONMENT=test pytest tests/ --ignore=tests/test_health.py --cov=app --cov-report=json:/tmp/coderoute-coverage.json -q --tb=short --disable-warnings
PYTHONPATH=. DATABASE_URL=sqlite+pysqlite:///:memory: AUTO_CREATE_TABLES=true ENVIRONMENT=test pytest -q tests/test_health.py
ruff check app/ tests/ --output-format=json
ruff check app/ tests/ --select E9,F63,F7,F82
python -m mypy app --ignore-missing-imports
pip-audit -r requirements.txt --format=json
ENVIRONMENT=test DATABASE_URL=sqlite+pysqlite:///:memory: python -m alembic heads
```

Depuis la racine :

```bash
ENVIRONMENT=test DATABASE_URL=sqlite+pysqlite:///:memory: python scripts/verify_migrations.py
PYTHONPATH=edge_agent ENVIRONMENT=test DATABASE_URL=sqlite+pysqlite:///:memory: pytest -q edge_agent/tests
```

Depuis frontend/ :

```bash
npm ci
npm run typecheck
npm run build
npm audit --json
npx playwright test --list
npx playwright install chromium
VITE_API_BASE_URL=http://localhost:8000 npx playwright test --workers=4 --timeout=15000 --retries=0 --reporter=json
```

## Interruption de sécurité et environnement

La revue automatique a refusé la poursuite de la suite pytest complète : elle a identifié un envoi potentiel vers Sentry dont le contenu n’était pas établi comme non sensible/autorisé. Aucun contournement ni relance équivalente après ce refus. Le bilan total et la couverture ne sont pas disponibles ; ne pas citer 84 % issu d’un audit précédent comme résultat local.

Préparer un harness de tests dont les clients de télémétrie, notification et fournisseur sont explicitement factices avant une nouvelle exécution ; revue du changement nécessaire pour éviter toute sortie réelle et préserver les tests dédiés à ces intégrations. Les résultats déjà acquis restent utilisables dans leur périmètre.

Le serveur Vite échoue sur uv_interface_addresses dans cet environnement ; Chromium ne s’installe pas non plus. Ce sont des échecs de préparation, pas des assertions UI échouées. PostgreSQL n’est pas disponible localement : le succès CI Fullstack Business E2E du parent applicatif est cité séparément dans AUDIT_PRODUCTION.md.

La première invocation Edge avait un PYTHONPATH erroné et 12 erreurs de collection ; correction de la commande, sans code modifié, puis résultat final 41/3 ci-dessus. Aucun secret réel n’a été lu. Le fichier pip-audit contient des entrées dupliquées : les 66 entrées ne sont pas 66 CVE uniques. Leur exploitabilité n’a pas été démontrée.
