# Production readiness

Ce document liste le minimum a verrouiller avant une presentation ou un pilote institutionnel CodeRoute Guinee.

## Configuration

1. Copier `.env.example` vers `.env`.
2. Definir `ENVIRONMENT=production`.
3. Remplacer `SECRET_KEY`, `ADMIN_REGISTRATION_TOKEN`, `POSTGRES_PASSWORD` et `BOOTSTRAP_ADMIN_PASSWORD`.
4. Configurer `CORS_ORIGINS` avec les domaines officiels uniquement.
5. Configurer `ALLOWED_HOSTS` avec le ou les hotes API officiels uniquement.
6. Garder `ENABLE_API_DOCS=false` en production; activer `/docs` uniquement en local ou recette fermee.
7. Garder `AUTO_CREATE_TABLES=false` en production: les tables doivent etre gerees par Alembic.
8. Ajuster `LOGIN_RATE_LIMIT_ATTEMPTS` et `LOGIN_RATE_LIMIT_WINDOW_SECONDS` selon la politique de securite.

## Base de donnees

```bash
docker compose up -d postgres
docker compose run --rm backend alembic upgrade head
```

Le conteneur backend execute aussi `alembic upgrade head` au demarrage pour appliquer les migrations disponibles.

## Runbook de mise en production

1. Preparer les secrets hors depot: cle JWT, token d'inscription admin, mot de passe PostgreSQL, compte bootstrap, URL publique API et origine frontend.
2. Executer le preflight de configuration.
3. Construire les images ou artefacts deployables depuis une branche taguee et testee.
4. Demarrer PostgreSQL puis appliquer les migrations Alembic.
5. Creer ou verifier le compte super administrateur avec le script bootstrap.
6. Executer les smoke tests locaux et verifier les endpoints publics.
7. Valider le go/no-go avec un responsable technique et un responsable metier avant ouverture aux centres.

Commandes minimales:

```bash
python scripts/preflight_deploy.py --env-file .env --target production
docker compose up -d postgres
docker compose run --rm backend alembic upgrade head
docker compose run --rm backend python -m app.bootstrap_admin
python scripts/smoke_local.py
```

Apres demarrage de l'API, relancer le preflight avec readiness:

```bash
python scripts/preflight_deploy.py --env-file .env --target production --api-url https://api.coderoute.gov.gn
```

## Sauvegardes et restauration

Plan minimum recommande:

- sauvegarde PostgreSQL quotidienne chiffree;
- retention de 30 jours pour le pilote, a ajuster par decision institutionnelle;
- test de restauration mensuel sur un environnement de recette;
- conservation separee des fichiers exportes et des journaux d'audit critiques.

Exemple de sauvegarde:

```bash
pg_dump "$DATABASE_URL" --format=custom --file=coderoute-guinee.backup
```

Exemple de restauration en recette:

```bash
pg_restore --clean --if-exists --dbname="$DATABASE_URL_RECETTE" coderoute-guinee.backup
docker compose run --rm backend alembic upgrade head
```

## Premier administrateur

Le compte de demonstration ne doit pas etre utilise en production. Creer ou verifier le super administrateur avec:

```bash
docker compose run --rm backend python -m app.bootstrap_admin
```

Le script lit:

- `BOOTSTRAP_ADMIN_EMAIL`
- `BOOTSTRAP_ADMIN_PASSWORD`
- `BOOTSTRAP_ADMIN_FULL_NAME`

Si l'utilisateur existe deja, le script le reactive et force son role `super_admin` sans changer son mot de passe.

## Securite HTTP et authentification

L'API ajoute des headers de securite par defaut:

- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `Referrer-Policy: same-origin`
- `Permissions-Policy` pour bloquer camera, micro et geolocalisation par defaut

Les tentatives de connexion echouees sont limitees par couple email/IP. Les evenements suivants sont historises dans `audit_logs`:

- `auth.login_success`
- `auth.login_failed`
- `auth.login_blocked`

En production, l'API doit egalement verifier:

- `ALLOWED_HOSTS` limite aux domaines API officiels, sans `localhost`, `127.0.0.1`, `testserver` ni wildcard;
- `ENABLE_API_DOCS=false` pour ne pas exposer Swagger/ReDoc publiquement;
- HTTPS termine au reverse proxy, avec header `Strict-Transport-Security` ajoute par l'API en mode production.

## Gouvernance des comptes

Les comptes sont consultables par les roles `admin` et `super_admin` via `/api/v1/users`.

Seul le role `super_admin` peut:

- creer un compte institutionnel avec mot de passe initial controle;
- reinitialiser le mot de passe d'un compte existant;
- changer le role d'un compte;
- activer ou suspendre un compte;
- reaffecter un compte vers `admin`, `center` ou `candidate`.

Les decisions sont historisees dans `audit_logs`:

- `user.created`
- `user.password_reset`
- `user.role_updated`
- `user.status_updated`

Un `super_admin` ne peut pas suspendre son propre compte ni se retrograder lui-meme.

Chaque utilisateur connecte peut changer son propre mot de passe via `/api/v1/auth/change-password`. Les changements et echecs sont historises avec:

- `auth.password_changed`
- `auth.password_change_failed`

## Monitoring minimal

Avant un pilote avec candidats reels, superviser au minimum:

- disponibilite `/health` et `/health/readiness`;
- erreurs backend et erreurs frontend;
- saturation disque, CPU, memoire et connexions PostgreSQL;
- connexions echouees, `auth.login_blocked` et changements de roles;
- paiements non rapproches ou rejetes;
- alertes du monitoring examen et sessions a risque eleve;
- taille des journaux d'audit et succes des exports CSV/PDF.

Les alertes critiques doivent identifier un responsable et un canal d'escalade.

## Controle avant presentation

```bash
docker compose up --build
python scripts/smoke_local.py
```

Puis verifier:

- `/health`
- `/health/readiness`
- statut `configuration` dans `/health/readiness`
- `/docs` uniquement hors production publique
- connexion administrateur
- dashboard national
- exports institutionnels
- export CSV du journal d'audit national
- parcours candidat jusqu'a convocation

## Checklist go/no-go

- `python scripts/preflight_deploy.py --env-file .env --target production --api-url ...` sans erreur.
- Domaine officiel et HTTPS valides.
- `CORS_ORIGINS` limite aux domaines autorises.
- `ALLOWED_HOSTS` limite aux hotes API officiels.
- `ENABLE_API_DOCS=false` en production publique.
- `AUTO_CREATE_TABLES=false` confirme.
- Migrations appliquees sans erreur.
- Super administrateur cree avec mot de passe non partage.
- Sauvegarde et restauration testees.
- Tests backend, build frontend et tests E2E verts.
- Procedure support centre documentee.
- Donnees de demonstration retirees des environnements officiels.
