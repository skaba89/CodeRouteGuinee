---
name: run-tests
description: Exécute les suites CodeRoute comme la CI (pytest backend, typecheck/build frontend, Playwright, edge) et rapporte les sorties réelles. À utiliser pour l'étape TESTS et toute vérification de non-régression.
---

# Exécuter les tests

## Backend (depuis `backend/`, variables identiques à `.github/workflows/ci.yml`)
```bash
export PYTHONPATH=. DATABASE_URL='sqlite+pysqlite:///:memory:' AUTO_CREATE_TABLES=true ENVIRONMENT=test
pytest tests/test_xxx.py -q --disable-warnings                 # ciblé
pytest tests/ --ignore=tests/test_health.py -q --disable-warnings --cov=app   # complet
```
Sans Python 3.12 local : exécuter dans `python:3.12-slim` avec `pip install -r backend/requirements.txt`,
sur une **copie** du dépôt, en supprimant toute copie de `.env` / `.env.demo` avant de lancer pytest.

Verrous (`with_for_update`, verrous consultatifs) et migrations : rejouer aussi sur PostgreSQL 16.

## Frontend
```bash
cd frontend && npm ci && npm run typecheck && npm run build && npm audit --audit-level=high
npx playwright test tests/e2e/<spec>.spec.ts
```

## Edge
```bash
cd edge_agent && pytest -q
```

## Répétition fonctionnelle
`scripts/demo.sh check` : parcours inscription → paiement → convocation → entrée → examen → résultat → supervision → audit.

## Invariants à garder verts
I1-I9 de `docs/audit/PLAN_TESTS_EXAMEN.md` §1 (confidentialité, trace, échéance, idempotence, banque d'entraînement exclue, périmètre centre, audit, gardes).

## Rapport
Commande exacte, nombre de tests passés/échoués, extrait d'échec. Ne jamais déclarer « vert » sans sortie.
