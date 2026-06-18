# Stabilite Docker et seed local

Cette note couvre les corrections issues de l audit sur le demarrage local.

## Ports configurables

Le backend Docker expose maintenant le port local via `BACKEND_PORT`.

```env
BACKEND_PORT=8000
FRONTEND_PORT=5173
```

Si `8000` est deja utilise :

```env
BACKEND_PORT=8010
```

Le frontend Docker construit automatiquement son URL API avec ce port si `VITE_API_BASE_URL` et `VITE_API_URL` ne sont pas definis.

## Seed demo protege

Le seed demo reste autorise en developpement :

```bash
docker compose exec backend python -m app.seed_demo
```

Hors `ENVIRONMENT=development`, il est bloque par defaut pour eviter d injecter le compte demo et les donnees fictives dans une base institutionnelle.

Pour une base jetable de demo/staging uniquement :

```bash
docker compose exec -e ALLOW_DEMO_SEED_NON_DEV=true backend python -m app.seed_demo
```

## Validation rapide

```bash
python scripts/smoke_local.py
```

ou, pour la recette automatisée :

```powershell
.\scripts\run_full_recette.cmd -Scope smoke
```
