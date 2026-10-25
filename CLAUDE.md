# CodeRoute Guinée — Instructions Claude Code

Plateforme nationale d'examen théorique du permis de conduire (DNTT). Intégrité
des examens et des résultats, confidentialité de la banque et données
personnelles des candidats priment sur la vitesse.

Pile : FastAPI + SQLAlchemy 2 + Alembic + PostgreSQL 16 (`backend/`), React 19 +
Vite + TypeScript (`frontend/`), passerelle hors-ligne des centres (`edge_agent/`),
déploiement Render (`render.yaml`). Audit et feuille de route : `docs/audit/`.

## Règles non négociables

1. **Secrets** : ne jamais lire, afficher, copier ni committer `.env*` (hors
   `*.example` / `*.template`), clés, jetons, ni une banque officielle importée.
2. **Clés de correction** : `correct_answer`, `correct_option_ids` et `explanation`
   ne sortent jamais vers un rôle `candidate` ou `center` (ni pendant l'épreuve,
   ni dans le résultat). Seuls `admin` / `super_admin` voient la correction.
3. **Réglementation** : ne jamais inventer de règle guinéenne. Tout paramètre
   d'examen non homologué reste « provisoire » et renvoie aux décisions R1-R20 de
   `docs/audit/ANALYSE_ECARTS_FRANCE_GUINEE.md` §4. Le modèle français est une
   référence de bonnes pratiques, pas la règle applicable.
4. **Intégrité** : ne pas affaiblir la trace d'examen, le verrou de tentative,
   l'audit HMAC chaîné (`audit_chain.py`) ni les gardes de démarrage.
5. **Pas de suppression** de fonctionnalité existante ; pas de changement de
   règle métier sans justification écrite.
6. **Tests** : toute modification ajoute des tests ; toute correction de sécurité
   ajoute un test de régression (IDOR, rôle, centre).
7. **Interdits sans validation explicite** : déploiement, fusion dans `main`
   (Render déploie automatiquement `main`), `git push --force`, suppression de
   branche, `alembic upgrade|downgrade` hors base jetable, `docker compose down -v`.
8. **Paiements** : Mobile Money et moyens locaux uniquement.

## Workflow

Changement important (examen, résultats, banque, auth, paiements, migration,
CI/infra, nouvel endpoint, > 3 fichiers) : plan écrit (fichiers, impacts, risques,
tests, rollback) → **attendre un « OK »** → implémentation → tests → revues
sécurité et domaine → PR (jamais de fusion automatique).

Agents : `.claude/agents/`. Skills : `.claude/skills/` (`audit`, `run-tests`,
`migration-check`, `security-review`, `exam-feature-validation`).

## Commandes

```bash
# Backend, comme en CI (depuis backend/)
PYTHONPATH=. DATABASE_URL=sqlite+pysqlite:///:memory: AUTO_CREATE_TABLES=true \
  ENVIRONMENT=test pytest tests/ --ignore=tests/test_health.py -q --disable-warnings
# Frontend
cd frontend && npm ci && npm run typecheck && npm run build && npx playwright test
# Démo locale et répétition du parcours complet
scripts/demo.sh init && scripts/demo.sh up && scripts/demo.sh seed 15 && scripts/demo.sh check
```

## Style

Code et identifiants en anglais ; commentaires, messages utilisateur et docs en
français. Python 3.12, `ruff` (`backend/ruff.toml`). Conventional Commits.
