# CodeRoute Guinee

CodeRoute Guinee est une plateforme nationale d'examen du code de la route pour la Republique de Guinee.

Le projet vise a digitaliser l'inscription, la reservation, le passage, la correction et la certification des examens theoriques du permis de conduire dans des centres agrees supervises par l'administration.

## Positionnement

CodeRoute Guinee est un produit national, pas un simple SaaS prive. La plateforme doit permettre a l'Etat, aux centres agrees, aux auto-ecoles et aux candidats de disposer d'un processus fiable, securise et tracable.

## Modules MVP

- Authentification et gestion des roles.
- Gestion des candidats.
- Gestion des centres agrees.
- Reservation des sessions d'examen.
- Convocation avec QR code.
- Banque de questions.
- Examen en ligne en centre agree.
- Correction automatique.
- Resultats securises.
- Tableau de bord administratif.
- Journal d'audit et premiers controles anti-fraude.

## Stack cible

- Frontend : React, Vite, TypeScript.
- Backend : FastAPI, Python.
- Base de donnees : PostgreSQL.
- Conteneurisation : Docker Compose.
- CI : GitHub Actions.

## Demarrage local

```bash
cp .env.example .env
docker compose up --build
```

Pour verrouiller la creation de comptes `admin` ou `super_admin` via `/api/v1/auth/register`,
configurez `ADMIN_REGISTRATION_TOKEN` et envoyez la meme valeur dans l'en-tete
`X-Admin-Registration-Token` lors des creations autorisees. Ce jeton doit etre active
en staging et production.

Endpoints :

- API : http://localhost:8000
- Swagger : http://localhost:8000/docs
- Frontend : http://localhost:5173

## Donnees de demonstration

Apres le demarrage des conteneurs :

```bash
docker compose exec backend python -m app.seed_demo
```

Le script prepare un jeu de donnees utilisable pour une demonstration : admin, centre agree, candidat, session, reservation, paiement, convocation, questions et resultat d'examen.

Pour un environnement institutionnel, utilisez plutot le bootstrap administrateur controle par variables d'environnement :

```bash
docker compose run --rm backend python -m app.bootstrap_admin
```

Consultez `docs/production_readiness.md` pour le demarrage PostgreSQL, les migrations Alembic et les variables critiques.

## Verification E2E locale rapide

```bash
python scripts/smoke_local.py
```

Ce script verifie les endpoints principaux : health, dashboard, convocation, paiement sandbox, validation entree centre et resume examen.

Pour le scenario complet de presentation, consulter :

```text
DEMO_LOCAL.md
```

## Roadmap

### Phase 1 - MVP national

- Socle backend et frontend.
- Gestion des candidats, centres, questions et sessions.
- Examen en ligne et correction automatique.
- Dashboard admin initial.

### Phase 2 - Securite renforcee

- Verification photo le jour de l'examen.
- Controle d'identite renforce.
- Logs anti-fraude.
- Detection de taux de reussite anormaux.
- Signature numerique des resultats.

### Phase 3 - Plateforme nationale avancee

- Paiement Mobile Money.
- Integration permis biometrique.
- Application mobile.
- API partenaires.
- BI nationale securite routiere.
