# CodeRoute Guinée — Démarrage rapide

## Prérequis
- Docker Desktop (Windows/Mac/Linux)
- Git

## Démarrage en 3 commandes

```bash
# 1. Cloner le projet
git clone https://github.com/skaba89/CodeRouteGuinee.git
cd CodeRouteGuinee

# 2. Configurer l'environnement
cp .env.dev .env

# 3. Démarrer
docker compose up --build
```

Puis dans un deuxième terminal, charger les données de test :
```bash
docker compose run --rm seed
```

## Accès

| Service | URL |
|---------|-----|
| Application | http://localhost:5173 |
| API | http://localhost:8000 |
| Documentation API (dev) | http://localhost:8000/docs |

## Comptes de test

| Rôle | Email | Mot de passe |
|------|-------|--------------|
| Super Admin | super_admin@coderoute.gov.gn | CodeRoute2026! |
| Admin national | admin.national@coderoute.gov.gn | CodeRoute2026! |
| Chef de centre (Conakry) | chef.conakry@coderoute.gov.gn | CodeRoute2026! |
| Chef de centre (Kindia) | chef.kindia@coderoute.gov.gn | CodeRoute2026! |
| Opérateur centre | operateur.conakry@coderoute.gov.gn | CodeRoute2026! |

## Candidats de test

| Référence | Nom | Scénario |
|-----------|-----|----------|
| GN-CAND-2026-001 | Mamadou Diallo | Admis 38/40 |
| GN-CAND-2026-002 | Fatoumata Camara | Ajourné 28/40 |
| GN-CAND-2026-003 | Alpha Bah | Score parfait 40/40 |
| GN-CAND-2026-004 | Mariam Soumah | Payé, session dans 14j |
| GN-CAND-2026-005 | Ibrahima Kouyaté | Réservé, paiement en attente |
| GN-CAND-2026-008 | Aminata Condé | Ajourné 34/40 (limite à 1 point) |

## Commandes utiles

```bash
# Démarrer en arrière-plan
docker compose up -d

# Voir les logs
docker compose logs -f backend
docker compose logs -f frontend

# Charger les données de test
docker compose run --rm seed

# Arrêter
docker compose down

# Tout réinitialiser (supprime les données)
docker compose down -v
```

## Résolution des problèmes courants

### Erreur `.pytest_cache: Accès refusé` ou `Permission denied` sur Windows
Ce problème est résolu automatiquement depuis la dernière version — les volumes anonymes
masquent `.pytest_cache` et le watcher ne surveille que `/app/app`.

Si vous rencontrez encore l'erreur avec une ancienne version :
```powershell
# Supprimer le cache localement
Remove-Item -Recurse -Force backend\.pytest_cache
# Forcer la recréation des conteneurs
docker compose down -v
docker compose up --build
```

### Le frontend ne se connecte pas à l'API
Vérifier dans `.env` :
```
VITE_API_BASE_URL=http://localhost:8000
```
> ⚠️ Depuis le navigateur, utilisez `localhost:8000` (pas le nom interne Docker `backend:8000`).

### Port déjà utilisé
Modifier dans `.env` :
```
BACKEND_PORT=8001
FRONTEND_PORT=5174
```

### Réinitialiser les données
```bash
docker compose down -v    # Supprime le volume PostgreSQL
docker compose up -d
docker compose run --rm seed
```
