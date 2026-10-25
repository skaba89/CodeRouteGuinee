# Agents et skills Claude Code — proposition

> **Proposition, non encore créée.** Le dépôt ne contient pas de dossier
> `.claude/`. Les fichiers ci-dessous seront ajoutés dans une PR dédiée après
> validation : `.claude/agents/*.md` et `.claude/skills/*/SKILL.md`.
> Conventions reprises du dépôt : français pour la doc et les messages, Python 3.12,
> tests dans `backend/tests/`, exécution des tests dans Docker, Conventional Commits.

## 1. Agents (8, sans redondance)

| Agent | Mission | Outils | Peut écrire ? |
|---|---|---|---|
| `software-architect` | Analyse d'impact, plan par fichier, vérification de conformité à `ARCHITECTURE_CIBLE.md` ; arbitre les migrations et les contrats d'API | Read, Grep, Glob, Bash (lecture) | Non |
| `backend-engineer` | Implémente un plan validé dans `backend/` (FastAPI, SQLAlchemy, Alembic) avec ses tests | Read, Edit, Write, Bash | Oui, `backend/` seulement |
| `frontend-ux-engineer` | Implémente un plan validé dans `frontend/` ; UX de l'épreuve, accessibilité, faible débit | Read, Edit, Write, Bash | Oui, `frontend/` seulement |
| `exam-domain-expert` | Gardien des règles d'examen : vérifie qu'aucune règle n'est inventée, que chaque paramètre renvoie à une décision R1-R20 ; relit la notation, la publication, la banque | Read, Grep, Glob | Non |
| `security-auditor` | Revue sécurité : authentification, IDOR, fuite de la banque, secrets, données personnelles, paiements ; exige un test de régression par faille | Read, Grep, Glob, Bash (lecture) | Non |
| `qa-automation-engineer` | Écrit et exécute les tests (pytest, Playwright, propriétés, charge) ; rapporte les sorties réelles | Read, Edit, Write, Bash | Fichiers de test uniquement |
| `devops-engineer` | CI GitHub Actions, Docker, `render.yaml`, scripts d'exploitation, edge ; **ne déploie jamais** | Read, Edit, Write, Bash | Oui, infrastructure, après validation |
| `documentation-reviewer` | Cohérence entre le README, `docs/` et le code ; signale les chiffres faux et les documents obsolètes | Read, Grep, Glob | Oui, `*.md` seulement |

Choix assumés : pas d'agent « database » séparé (le `software-architect` relit les
migrations avec le skill `migration-check`) ; pas d'agent « performance » au départ
(campagne de charge portée par `qa-automation-engineer`).

### Règles communes (bloc commun à tous les agents)
- Ne jamais lire, afficher ni committer `.env*` (hors `*.example`/`*.template`), clés, jetons, ni la banque officielle importée.
- Ne jamais exposer `correct_answer`, `correct_option_ids` ou `explanation` dans une réponse candidat ou centre.
- Ne jamais inventer de règle réglementaire guinéenne : marquer `À CONFIRMER DNTT` et renvoyer à `ANALYSE_ECARTS_FRANCE_GUINEE.md` §4.
- Aucun déploiement, aucune fusion dans `main`, aucun `push --force`.
- Toute modification s'accompagne de tests ; toute correction de sécurité, d'un test de régression.

## 2. Skills réutilisables (5)

| Skill | Déclenchement | Contenu |
|---|---|---|
| `audit` | Audit d'un module ou du dépôt | Grille des 10 points de l'audit initial ; classement ✅/🟡/❌/❔ ; preuve `fichier:ligne` obligatoire ; risques classés critique/élevé/moyen/faible |
| `run-tests` | Étape TESTS / non-régression | Commandes exactes : image `coderoute-test:py312`, `pytest` complet et ciblé, `npm run typecheck && npm run build`, Playwright ; règle « citer la sortie réelle » ; invariants I1-I10 |
| `migration-check` | Toute migration Alembic ou modification de modèle | Une seule tête ; migration additive et réversible ; `upgrade/downgrade/upgrade` sur PostgreSQL 16 ; pas de DDL au démarrage ; compatibilité ascendante pendant le déploiement |
| `security-review` | PR touchant auth, examen, résultats, banque, paiements, données personnelles | Liste de contrôle `PLAN_SECURITE.md` §3 ; scénario d'exploitation ; test attendu |
| `exam-feature-validation` | Toute fonctionnalité d'examen | Vérifie : confidentialité des clés (I1, I2, I10), trace et révision, chronométrage et reprise, idempotence, règle versionnée et non inventée, accessibilité, comportement hors-ligne ; exécute `scripts/demo.sh check` |

## 3. Workflow proposé

```text
Demande → software-architect (plan) → ⛔ validation humaine
        → backend-engineer / frontend-ux-engineer (implémentation)
        → qa-automation-engineer (tests, sorties réelles)
        → security-auditor + exam-domain-expert (revues, en parallèle)
        → documentation-reviewer → PR (pas de fusion automatique)
```

## 4. Prochaine étape
Sur votre validation : PR `chore(claude): agents et skills du projet`, avec les
8 fichiers d'agents, les 5 skills et un `CLAUDE.md` racine qui reprend les règles
communes. Aucun fichier applicatif touché.
