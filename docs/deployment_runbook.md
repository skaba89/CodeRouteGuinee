# Runbook de deploiement - CodeRoute Guinee

Ce runbook sert de procedure courte pour une mise en recette, staging ou production.

## 1. Avant de deployer

- Branche ou tag valide par CI.
- Variables d'environnement preparees hors depot.
- Sauvegarde de la base existante disponible.
- Responsable technique et responsable metier identifies.
- Fenetre de deploiement communiquee aux centres pilotes.

## 2. Preflight configuration

```bash
python scripts/preflight_deploy.py --env-file .env --target staging
python scripts/preflight_deploy.py --env-file .env --target production
```

Le preflight doit terminer sans `ERROR`. Les `WARN` restants doivent etre acceptes explicitement par le responsable technique.

## 3. Deploiement applicatif

```bash
docker compose pull
docker compose build
docker compose up -d postgres
docker compose run --rm backend alembic upgrade head
docker compose up -d backend frontend
```

Verifier ensuite:

```bash
python scripts/preflight_deploy.py --env-file .env --target production --api-url https://api.coderoute.gov.gn
python scripts/smoke_local.py
```

Adapter `CODEROUTE_API_URL` et `CODEROUTE_FRONTEND_URL` pour staging ou production.

## 4. Go/no-go

Go uniquement si:

- `/health` retourne `ok`;
- `/health/readiness` ne contient aucune erreur de configuration;
- migrations appliquees;
- super administrateur disponible;
- export PDF dossier Etat telechargeable;
- convocation PDF telechargeable;
- parcours candidat pilote valide;
- journal d'audit consultable;
- aucun incident critique ouvert.

## 5. Rollback

Rollback si:

- API indisponible plus de 10 minutes;
- migrations bloquantes ou donnees critiques incoherentes;
- connexion admin impossible;
- paiement ou convocation pilote non fonctionnel;
- readiness en erreur apres correction de configuration.

Actions:

```bash
docker compose logs backend
docker compose down
```

Restaurer la derniere image valide et, si necessaire, la sauvegarde PostgreSQL validee avant deploiement.

## 6. Apres deploiement

- Exporter le rapport institutionnel PDF.
- Exporter le journal d'audit CSV.
- Noter l'heure de bascule, le commit, le responsable et les incidents.
- Planifier une revue 24h apres ouverture aux centres pilotes.
