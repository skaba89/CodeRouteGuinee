# Production readiness

Ce document liste le minimum a verrouiller avant une presentation ou un pilote institutionnel CodeRoute Guinee.

## Configuration

1. Copier `.env.example` vers `.env`.
2. Remplacer `SECRET_KEY`, `ADMIN_REGISTRATION_TOKEN`, `POSTGRES_PASSWORD` et `BOOTSTRAP_ADMIN_PASSWORD`.
3. Configurer `CORS_ORIGINS` avec les domaines officiels uniquement.
4. Garder `AUTO_CREATE_TABLES=false` en production: les tables doivent etre gerees par Alembic.
5. Ajuster `LOGIN_RATE_LIMIT_ATTEMPTS` et `LOGIN_RATE_LIMIT_WINDOW_SECONDS` selon la politique de securite.

## Base de donnees

```bash
docker compose up -d postgres
docker compose run --rm backend alembic upgrade head
```

Le conteneur backend execute aussi `alembic upgrade head` au demarrage pour appliquer les migrations disponibles.

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

## Controle avant presentation

```bash
docker compose up --build
python scripts/smoke_local.py
```

Puis verifier:

- `/health`
- `/health/readiness`
- `/docs`
- connexion administrateur
- dashboard national
- exports institutionnels
- parcours candidat jusqu'a convocation
