# CodeRoute Guinée 🇬🇳

Plateforme nationale d'examen du code de la route — République de Guinée.

Digitalisation complète : inscription, réservation, passage, correction et certification des examens théoriques du permis de conduire dans des centres agréés supervisés par la DNTT / Ministère des Transports.

---

## Démarrage rapide (développement)

```bash
git clone https://github.com/skaba89/CodeRouteGuinee.git
cd CodeRouteGuinee
cp .env.dev .env
docker compose up --build
# Charger les données de test (candidats, centres, 40 questions, sessions)
docker compose exec backend python -m app.seed_full
```

→ **Application** : http://localhost:5173  
→ **API + Swagger** : http://localhost:8000/docs

## Démonstration institutionnelle (DNTT)

Environnement prêt à présenter (comptes par rôle, activité nationale sur
8 régions, session « en direct », journal d'audit chaîné) et script de 15 minutes :
voir [`DEMO.md`](DEMO.md).

```bash
scripts/demo.sh init && scripts/demo.sh up && scripts/demo.sh seed 15 && scripts/demo.sh check
```

---

## Déploiement production

Production sur le VPS OVH, à côté d'Academy Guinéenne : voir
[`deploy/vps/README.md`](deploy/vps/README.md).

```bash
cp deploy/vps/.env.vps.example .env.vps   # remplir les secrets
./deploy/vps/deploy.sh                    # build, migrations, redémarrage, contrôle
./deploy/vps/scripts/creer-admin.sh       # premier super-administrateur
```

> Les seeds de démonstration (`seed_full`, `seed_demo`, `seed_demo_dntt`) sont
> **refusés en production**, sans dérogation possible : ils créent des comptes à
> mot de passe connu. Centres, candidats et banque officielle s'importent depuis
> l'administration (imports officiels CSV), après validation DNTT.

Render n'est plus utilisé (`render.yaml` inactif).

---

## Architecture

```
CodeRoute Guinée
├── backend/              FastAPI + SQLAlchemy + PostgreSQL
│   ├── app/
│   │   ├── routers/     63 modules de routes REST
│   │   └── models_*     modèles SQLAlchemy
│   ├── alembic/         17 migrations (une seule tête)
│   └── tests/           ~1 300 tests pytest (couverture 84 %, bloquants en CI)
├── frontend/             React 19 + TypeScript + Vite
│   ├── src/pages/       pages candidat, centre, auto-école, admin, ministère
│   └── tests/e2e/       21 specs Playwright
├── edge_agent/          Passerelle hors-ligne des centres d'examen
├── nginx/               Reverse-proxy (4096 connexions)
├── scripts/             Backup PG, preflight, inventaire audio
└── .github/workflows/   CI/CD + backup automatique quotidien
```

## Stack technique

| Couche | Technologie |
|---|---|
| API | FastAPI 0.115, Python 3.12, Gunicorn + Uvicorn |
| Base de données | PostgreSQL 16, SQLAlchemy 2, Alembic |
| Frontend | React 19, TypeScript strict, Vite 8 |
| Reverse-proxy | Nginx 1.27 (worker_connections 4096) |
| Conteneurs | Docker Compose (dev + prod) |
| CI/CD | GitHub Actions (tests, coverage, Playwright, backup) |

## Fonctionnalités

- **Authentification JWT** — 5 rôles : super_admin, admin, center, driving_school, candidate
- **Banque de questions gouvernée** — workflow de validation, médias contrôlés, banque d'entraînement séparée. Le dépôt ne contient que des questions de démonstration (40 « officielles » de test + 160 d'entraînement, en français) : la banque officielle reste à fournir par la DNTT (voir `docs/audit/`)
- **Examens chronométrés** — 40 questions / 30 min / seuil 35/40 (paramètres provisoires, à homologuer), autosauvegarde serveur et reprise
- **Paiements Mobile Money** — Orange Money, Wave, MTN MoMo, Moov Money
- **Notifications email** — Brevo (confirmation réservation, convocation, résultats, certificat)
- **Dashboard national** — KPIs temps réel : taux de réussite, revenus GNF, sessions/semaine
- **Certificats numériques** — QR code vérifiable publiquement
- **Export CSV/PDF** — rapports institutionnels DNTT
- **Anti-fraude** — monitoring examen, alertes incidents, audit logs complet
- **Pagination server-side** — 11 endpoints avec limit/offset/search

## Scalabilité

| Serveur | Utilisateurs simultanés | rps |
|---|---|---|
| 2 CPU / 4 Go | ~500 | ~100 |
| 4 CPU / 8 Go | ~2 000 | ~400 |
| 8 CPU / 16 Go | ~5 000 | ~800 |

Voir `SCALING.md` pour le guide de dimensionnement complet.

## Comptes de test

Les comptes de développement et de démonstration (mot de passe commun, bases
jetables uniquement) sont décrits dans [`DEMO.md`](DEMO.md) et
[`QUICKSTART.md`](QUICKSTART.md).

## Audit et feuille de route

État des lieux, écarts avec les bonnes pratiques françaises, décisions DNTT à
obtenir et plan d'évolution : [`docs/audit/`](docs/audit/).

## Variables d'environnement requises

Voir `.env.example` pour la liste complète avec documentation.

Variables critiques pour la production :
```env
SECRET_KEY=<64 caractères aléatoires>
DATABASE_URL=postgresql+psycopg://user:pass@postgres:5432/db
BREVO_API_KEY=xkeysib-...
WAVE_API_KEY=wave_sn_prod_...
WAVE_WEBHOOK_SECRET=...
ORANGE_MONEY_CLIENT_ID=...
```

## Tests

```bash
cd backend
pip install -r requirements.txt
PYTHONPATH=. DATABASE_URL=sqlite+pysqlite:///:memory: AUTO_CREATE_TABLES=true ENVIRONMENT=test \
  pytest tests/ --ignore=tests/test_health.py -q
# Couverture : 84 %
```

```bash
cd frontend
npm install
npm run typecheck
npm run build
npx playwright test   # Tests E2E UI
```
