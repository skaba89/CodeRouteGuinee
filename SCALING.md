# Guide de dimensionnement — CodeRoute Guinée

## Formules de calcul

```
workers          = 2 × nb_CPU + 1
pool_total       = workers × (DB_POOL_SIZE + DB_MAX_OVERFLOW)
pg_max_conn      ≥ pool_total + 10   # réserver 10 pour pgAdmin/monitoring
nginx_max_conn   = worker_processes × worker_connections
```

## Configurations recommandées par taille de serveur

### Serveur minimal (2 CPU / 4 Go RAM) — ~500 utilisateurs simultanés
```env
WEB_CONCURRENCY=5
DB_POOL_SIZE=15
DB_MAX_OVERFLOW=20
# pool_total = 5 × 35 = 175 → PG max_connections ≥ 185
```
PostgreSQL : `max_connections=200 shared_buffers=256MB`

### Serveur standard (4 CPU / 8 Go RAM) — ~2 000 utilisateurs simultanés
```env
WEB_CONCURRENCY=9
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=30
# pool_total = 9 × 50 = 450 → PG max_connections ≥ 460
```
PostgreSQL : `max_connections=500 shared_buffers=512MB effective_cache_size=1536MB`

### Serveur large (8 CPU / 16 Go RAM) — ~5 000 utilisateurs simultanés
```env
WEB_CONCURRENCY=17
DB_POOL_SIZE=25
DB_MAX_OVERFLOW=40
# pool_total = 17 × 65 = 1105 → PG max_connections ≥ 1115
```
PostgreSQL : `max_connections=1200 shared_buffers=1GB effective_cache_size=4GB work_mem=16MB`

### Serveur XL (16 CPU / 32 Go RAM) — ~10 000+ utilisateurs simultanés
```env
WEB_CONCURRENCY=33
DB_POOL_SIZE=30
DB_MAX_OVERFLOW=50
# pool_total = 33 × 80 = 2640 → ajouter PgBouncer (pooler externe)
```
À ce niveau : utiliser **PgBouncer** en transaction mode entre FastAPI et PostgreSQL.

---

## Bottlenecks par ordre d'impact

| Rang | Goulot | Config actuelle | Optimisé |
|---|---|---|---|
| 1 | Workers Uvicorn | 2 | 2×CPU+1 (Gunicorn) |
| 2 | Pool connexions DB | 5+10 par worker | 20+30 par worker |
| 3 | PostgreSQL max_connections | 100 (défaut) | 500 (configuré) |
| 4 | Nginx worker_connections | 1024 | 4096 |
| 5 | Keepalive upstream | 32 | 128 |
| 6 | Rate limiting API | 30 req/min | 120 req/min |
| 7 | Synchronous_commit | on (défaut) | local (10× plus rapide) |

## Prochaines étapes pour aller plus loin

### PgBouncer (> 5 000 utilisateurs)
Pooler de connexions externe entre FastAPI et PostgreSQL.
Réduit le nombre réel de connexions PostgreSQL sans changer le code.
```yaml
# À ajouter dans docker-compose.prod.yml
pgbouncer:
  image: bitnami/pgbouncer:1.23
  environment:
    POSTGRESQL_HOST: postgres
    POSTGRESQL_DATABASE: ${POSTGRES_DB}
    PGBOUNCER_POOL_MODE: transaction
    PGBOUNCER_MAX_CLIENT_CONN: 5000
    PGBOUNCER_DEFAULT_POOL_SIZE: 50
```

### Migration async (> 10 000 utilisateurs)
Passer SQLAlchemy sync → async avec asyncpg.
Chaque worker gère des centaines de requêtes simultanément.
Gain estimé : ×5 à ×10 en débit.
Durée de migration : 3–5 jours.

### Horizontal scaling (> 50 000 utilisateurs)
Docker Swarm ou Kubernetes avec plusieurs replicas backend.
Nécessite un load balancer externe (HAProxy ou AWS ALB).
La session JWT est stateless → compatible multi-instances sans modification.

