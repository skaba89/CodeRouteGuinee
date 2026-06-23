# Démarrage local — CodeRoute Guinée

## Prérequis

- Docker Desktop (Windows/Mac) ou Docker Engine (Linux)
- Git

## Démarrage en 3 commandes

```bash
# 1. Cloner le projet
git clone https://github.com/skaba89/CodeRouteGuinee.git
cd CodeRouteGuinee

# 2. Lancer en mode développement
docker compose -f docker-compose.dev.yml up --build

# 3. (Optionnel) Charger les données de démonstration
docker compose -f docker-compose.dev.yml run --rm seed
```

## Accès

| Service | URL |
|---|---|
| Frontend | http://localhost:5173 |
| API / Swagger | http://localhost:8000/docs |
| Healthcheck | http://localhost:8000/health |
| PostgreSQL | localhost:5435 (user: coderoute / pass: coderoute) |

## Comptes de test (après seed)

| Rôle | Email | Mot de passe |
|---|---|---|
| Super Admin | super_admin@coderoute.gov.gn | CodeRoute2026! |
| Admin national | admin.national@coderoute.gov.gn | CodeRoute2026! |
| Chef centre | chef.conakry@coderoute.gov.gn | CodeRoute2026! |

## Commandes utiles

```bash
# Voir les logs du backend
docker compose -f docker-compose.dev.yml logs -f backend

# Redémarrer uniquement le backend (après modif Python)
docker compose -f docker-compose.dev.yml restart backend

# Arrêter tout
docker compose -f docker-compose.dev.yml down

# Arrêter et supprimer les données PostgreSQL
docker compose -f docker-compose.dev.yml down -v

# Lancer les tests
docker compose -f docker-compose.dev.yml exec backend \
  sh -c "PYTHONPATH=. pytest tests/ --ignore=tests/test_health.py -q"
```

## ⚠️ Erreurs fréquentes

### "coderoute-backend-dev is unhealthy"

Voir les logs pour diagnostiquer :
```bash
docker compose -f docker-compose.dev.yml logs backend
```

Causes fréquentes :
- PostgreSQL pas encore prêt → attendre 30 secondes et relancer
- Migration Alembic échouée → voir les logs
- Port 8000 déjà utilisé → changer `BACKEND_PORT=8001` dans `.env.dev`

### "Cannot find module" ou erreur TypeScript

Le volume node_modules peut être corrompu sur Windows :
```bash
docker compose -f docker-compose.dev.yml down -v
docker compose -f docker-compose.dev.yml up --build
```

### Pas de `docker-compose.dev.yml` (ancienne version)

Utiliser le fichier par défaut :
```bash
cp .env.dev .env
docker compose up --build
```

## ❌ Ne pas utiliser `docker-compose.prod.yml` en local

Ce fichier est pour la production uniquement (Gunicorn, Nginx, SSL).  
Il nécessite des variables d'env réelles (SECRET_KEY, DATABASE_URL PostgreSQL externe, etc.)
