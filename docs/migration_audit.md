# Audit migrations Alembic

Cette verification garantit que le projet peut repartir d une base vide avec les migrations seules, sans `AUTO_CREATE_TABLES`.

## Commande

Depuis le dossier `backend`:

```bash
python ../scripts/verify_migrations.py
```

La commande effectue :

1. creation d une base SQLite temporaire vide;
2. `alembic upgrade head`;
3. execution de `tests/test_database_migrations.py`;
4. execution de `python -m app.seed_demo` avec `AUTO_CREATE_TABLES=false`.

## Criteres d acceptation

- Toutes les tables du metadata SQLAlchemy existent apres migration.
- La table `questions` contient les champs multimedia `media_type`, `media_url`, `media_alt`.
- La version Alembic finale est `20260618_0002`.
- Le seed demo fonctionne sur une base creee uniquement par migrations.

## Pourquoi c est important

En production, les tables ne doivent pas etre creees automatiquement par l application. Le schema doit etre entierement reproductible via Alembic.
