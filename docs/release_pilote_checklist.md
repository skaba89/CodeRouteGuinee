# Checklist release pilote

Cette checklist sert de controle court avant une recette ou une presentation institutionnelle.

## 1. CI verte

- Workflow GitHub Actions termine sans erreur.
- Jobs backend, frontend build, E2E et release preflight verts.
- Aucun artefact de test critique non consulte.

## 2. Configuration

- `.env` de l'environnement cible valide par:

```bash
python scripts/preflight_deploy.py --env-file .env --target production
```

- `CORS_ORIGINS` limite aux domaines officiels.
- `ALLOWED_HOSTS` limite aux hotes API officiels.
- `ENABLE_API_DOCS=false` en production publique.
- `AUTO_CREATE_TABLES=false`.
- `BACKUP_RETENTION_DAYS>=7` et `BACKUP_ENCRYPTION_REQUIRED=true`.

## 3. Donnees et sauvegarde

- Sauvegarde PostgreSQL realisee avant bascule:

```bash
python scripts/postgres_backup.py --env-file .env backup
```

- Test de restauration execute en recette.
- Donnees de demonstration retirees de l'environnement officiel.
- Imports officiels testes en simulation avant ecriture.

## 4. Go/no-go fonctionnel

- `/health` retourne `ok`.
- `/health/readiness` ne contient aucune erreur.
- `/api/v1/operations/summary` ne retourne pas `critical`.
- Recette pilote institutionnelle executee:

```bash
pytest backend/tests/test_e2e_institutional_pilot_recipe.py
```

- Recette examen multimedia 40 questions executee:

```bash
pytest backend/tests/test_e2e_candidate_center_multimedia_exam.py
```

- Connexion super admin reelle validee.
- Parcours candidat pilote valide: dossier, paiement, convocation, examen, resultat.
- Exports PDF/CSV institutionnels telecharges.
- Journal d'audit consultable et exportable.

## 5. Validation metier

- Responsable technique identifie.
- Responsable metier identifie.
- Fenetre de deploiement communiquee.
- Canal d'escalade ouvert.
- Decision go/no-go notee avec commit, date et environnement.
