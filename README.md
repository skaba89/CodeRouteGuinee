# CodeRoute Guinée 🇬🇳

Plateforme nationale d'examen du code de la route — République de Guinée.

Digitalisation complète : inscription, réservation, passage, correction et certification des examens théoriques du permis de conduire dans des centres agréés supervisés par la DNTT / Ministère des Transports.

---

## Démarrage rapide

```bash
git clone https://github.com/skaba89/CodeRouteGuinee.git
cd CodeRouteGuinee
cp .env.dev .env
docker compose up --build
docker compose run --rm seed   # Charge les données de test
```

→ **Application** : http://localhost:5173  
→ **API + Swagger** : http://localhost:8000/docs

---

## Comptes de test

| Rôle | Email | Mot de passe |
|---|---|---|
| Super Admin | super_admin@coderoute.gov.gn | CodeRoute2026! |
| Admin national | admin.national@coderoute.gov.gn | CodeRoute2026! |
| Chef de centre (Conakry) | chef.conakry@coderoute.gov.gn | CodeRoute2026! |
| Chef de centre (Kindia) | chef.kindia@coderoute.gov.gn | CodeRoute2026! |
| Opérateur centre | operateur.conakry@coderoute.gov.gn | CodeRoute2026! |

### Candidats de test

| Référence | Nom | Scénario |
|---|---|---|
| GN-CAND-2026-001 | Mamadou Diallo | Admis 38/40 |
| GN-CAND-2026-002 | Fatoumata Camara | Ajourné 28/40 |
| GN-CAND-2026-003 | Alpha Bah | Score parfait 40/40 |
| GN-CAND-2026-004 | Mariam Soumah | Payé, session dans 14j |
| GN-CAND-2026-008 | Aminata Condé | Ajourné 34/40 (limite) |

---

## Architecture

```
CodeRouteGuinée/
├── backend/               FastAPI + SQLAlchemy + Alembic
│   ├── app/
│   │   ├── routers/       28 routers (80 endpoints)
│   │   ├── models_*.py    19 modèles SQLAlchemy
│   │   ├── migrations/    3 migrations Alembic
│   │   ├── exam_engine.py Moteur d'examen officiel
│   │   └── seed_full.py   Données de test complètes
│   └── tests/             148 tests, 81% couverture
├── frontend/              React 18 + Vite + TypeScript
│   └── src/
│       ├── pages.tsx      Toutes les pages (7 rôles)
│       ├── api.ts         80 fonctions API
│       └── styles.css     Design system
├── nginx/                 Config Nginx prod + TLS
├── database/              init.sql PostgreSQL
└── docker-compose*.yml    Dev + Prod
```

## Stack technique

| Composant | Technologie |
|---|---|
| Frontend | React 18, Vite, TypeScript strict |
| Backend | FastAPI, Python 3.12, SQLAlchemy 2.0 |
| Base de données | PostgreSQL 16 |
| Auth | JWT HS256 + refresh token 7j |
| Migrations | Alembic (3 migrations) |
| Tests | pytest, 148 tests, 81% couverture |
| CI | GitHub Actions (6 jobs parallèles) |
| Conteneurs | Docker Compose (dev + prod) |
| Reverse proxy | Nginx 1.27, TLS 1.2/1.3 |
| Monitoring | Sentry (optionnel) |
| Mobile Money | Orange Money GN + MTN MoMo |
| i18n | 5 langues (fr, Pular, Malinké, Soussou, en) |

---

## Fonctionnalités par rôle

### 🎓 Candidat
- Paiement Mobile Money (Orange Money, MTN Money)
- Téléchargement convocation PDF avec QR code
- Passage examen en ligne (40 questions, 30 min, timer)
- Résultats détaillés avec corrections et explications
- Vérification et téléchargement du certificat PDF

### 🏢 Centre agréé
- Validation d'entrée candidat (scan QR / code de vérification)
- Démarrage d'examen depuis référence de réservation
- Supervision des postes en temps réel
- Déclaration et suivi des incidents

### 👨‍💼 Admin national
- Dashboard national (candidats, centres, sessions, fraudes)
- Gestion des candidats (liste, import officiel)
- Gestion des paiements et réconciliation financière
- Monitoring examens et détection des anomalies
- Gouvernance de la banque de questions
- Audit logs complets avec export CSV
- Gestion des comptes utilisateurs

### 🔐 Super Admin
- Toutes les fonctions admin
- Création de comptes institutionnels
- Rapport institutionnel PDF
- Audit complet et exports

---

## Examen officiel

- **40 questions** tirées aléatoirement par catégorie (répartition officielle DNTT)
- **30 minutes** chronomètre bloquant
- **Seuil d'admission : 35/40** (87,5 %)
- 8 catégories : signalisation, priorités, vitesse, dépassement, sécurité passive, urgence, alcool/drogues, premiers secours
- Questions illustrées (panneaux SVG, scènes de circulation)
- Résultats avec correction détaillée par question

---

## Déploiement production

```bash
# 1. Générer les certificats TLS
./nginx/generate_certs.sh letsencrypt coderoute.gov.gn admin@coderoute.gov.gn

# 2. Configurer les variables d'environnement
cp .env.prod.example .env
# Éditer .env : SECRET_KEY, DATABASE_URL, Mobile Money, Sentry...

# 3. Démarrer
docker compose -f docker-compose.prod.yml up -d

# 4. Bootstrap super_admin (premier démarrage uniquement)
docker compose -f docker-compose.prod.yml exec backend \
  python -c "from app.bootstrap_admin import bootstrap; bootstrap()"
```

**Ports exposés en production :**
- 80 → redirect HTTPS
- 443 → Nginx (frontend + API via reverse proxy)

---

## CI/CD

6 jobs GitHub Actions sur chaque PR :

| Job | Description |
|---|---|
| `backend-lint` | ruff check (zéro avertissement) |
| `backend-tests` | pytest 148 tests en parallèle |
| `backend-coverage` | Couverture ≥ 80% (seuil bloquant) |
| `frontend-build` | npm run build + typecheck |
| `frontend-ui-tests` | Playwright (structure) |
| `release-preflight` | Validation finale avant merge |

+ Cron quotidien : backup PostgreSQL à 02h00 UTC

---

## Variables d'environnement

Voir `.env.dev` (développement) et `.env.prod.example` (production documenté).

Variables clés :
- `SECRET_KEY` : clé JWT (générer avec `openssl rand -hex 32`)
- `DATABASE_URL` : connexion PostgreSQL
- `MOBILE_MONEY_MODE` : `sandbox` (dev) ou `production`
- `SENTRY_DSN` : monitoring erreurs (optionnel)
- `ADMIN_REGISTRATION_TOKEN` : protection création comptes admin

---

## Résolution de problèmes

### Docker — `.pytest_cache: Permission denied` (Windows)
```powershell
Remove-Item -Recurse -Force backend\.pytest_cache
docker compose down && docker compose up --build
```

### Frontend ne se connecte pas à l'API
Vérifier dans `.env` : `VITE_API_BASE_URL=http://localhost:8000`

### Reset complet des données
```bash
docker compose down -v
docker compose up -d
docker compose run --rm seed
```

---

## Licence

Développé par **DataSphere Innovation** pour la République de Guinée.  
Tous droits réservés — usage institutionnel.
