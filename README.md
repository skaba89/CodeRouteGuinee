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

---

## Déploiement production

```bash
# 1. Configurer les variables d'environnement
cp .env.example .env
# Éditer .env avec les vraies valeurs (Brevo, Wave, Orange Money, MTN)

# 2. Déployer
docker compose -f docker-compose.prod.yml up -d

# 3. Appliquer les migrations
docker compose -f docker-compose.prod.yml exec backend alembic upgrade head

# 4. Créer le premier super-admin
docker compose -f docker-compose.prod.yml exec backend \
  python -m app.bootstrap_admin

# 5. Charger les données initiales (questions, centres DNTT)
docker compose -f docker-compose.prod.yml exec backend \
  ALLOW_SEED_IN_PROD=true python -m app.seed_full
```

→ **API** : https://api.coderoute.gov.gn  
→ **Frontend** : https://coderoute.gov.gn

---

## Architecture

```
CodeRoute Guinée
├── backend/              FastAPI + SQLAlchemy + PostgreSQL
│   ├── app/
│   │   ├── routers/     111 endpoints API REST
│   │   ├── models_*     19 modèles SQLAlchemy
│   │   └── alembic/     5 migrations
│   └── tests/           404+ tests (83% coverage)
├── frontend/             React 19 + TypeScript + Vite
│   ├── src/pages/       10 pages (éclatées depuis pages.tsx)
│   └── tests/e2e/       Tests Playwright
├── nginx/               Reverse-proxy (4096 connexions)
├── scripts/             Backup PG, preflight, inventaire audio
└── .github/workflows/   CI/CD + backup automatique quotidien
```

## Stack technique

| Couche | Technologie |
|---|---|
| API | FastAPI 0.115, Python 3.12, Gunicorn + Uvicorn |
| Base de données | PostgreSQL 16, SQLAlchemy 2, Alembic |
| Frontend | React 19, TypeScript strict, Vite 6 |
| Reverse-proxy | Nginx 1.27 (worker_connections 4096) |
| Conteneurs | Docker Compose (dev + prod) |
| CI/CD | GitHub Actions (tests, coverage, Playwright, backup) |

## Fonctionnalités

- **Authentification JWT** — 5 rôles : super_admin, admin, center, driving_school, candidate
- **Banque de 19 600 questions** — 8 catégories, 8 langues (audio TTS Web Speech API)
- **Examens chronométrés** — 40 questions / 30 min / seuil 35/40 avec scoring automatique
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

## Comptes de test (après seed)

| Rôle | Email | Mot de passe |
|---|---|---|
| Super Admin | super_admin@coderoute.gov.gn | CodeRoute2026! |
| Admin national | admin.national@coderoute.gov.gn | CodeRoute2026! |
| Chef centre Conakry | chef.conakry@coderoute.gov.gn | CodeRoute2026! |

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
pytest tests/ --ignore=tests/test_health.py -q
# Coverage : 83%+
```

```bash
cd frontend
npm install
npm run typecheck
npm run build
npx playwright test   # Tests E2E UI
```
