"""
Configuration Gunicorn pour CodeRoute Guinée — production.

Gunicorn comme process manager + Uvicorn workers :
  - Gunicorn gère le cycle de vie des workers (restart automatique, graceful reload)
  - UvicornWorker gère les connexions HTTP/2 et WebSocket asynchrones
  - Chaque worker = un process Python indépendant (pas de GIL entre eux)

Calcul des workers :
  Règle générale : 2 × nb_CPU + 1
  Ex : serveur 4 CPU → 9 workers
  En conteneur Docker : lire /proc/cpuinfo ou utiliser la variable WEB_CONCURRENCY

Calcul des connexions DB :
  workers × (pool_size + max_overflow) ≤ max_connections PostgreSQL - 10 (réservés)
  Ex : 9 × 50 = 450 → PostgreSQL max_connections = 500
"""
import multiprocessing
import os

# ── Workers ──────────────────────────────────────────────────────────────────
_cpu_count   = multiprocessing.cpu_count()
workers      = int(os.getenv("WEB_CONCURRENCY", (2 * _cpu_count) + 1))
worker_class = "uvicorn.workers.UvicornWorker"

# ── Timeouts ─────────────────────────────────────────────────────────────────
timeout          = 60   # worker tué après 60s (protège contre les requêtes zombies)
graceful_timeout = 30   # délai de grâce avant SIGKILL lors d'un reload
keepalive        = 5    # secondes de keepalive HTTP

# ── Connexions ────────────────────────────────────────────────────────────────
worker_connections = 1000   # connexions simultanées max par worker (async)

# ── Réseau ───────────────────────────────────────────────────────────────────
bind            = "0.0.0.0:8000"
backlog         = 2048          # taille de la file d'attente TCP

# ── Performance ──────────────────────────────────────────────────────────────
preload_app     = True          # charge l'app AVANT de forker → partage mémoire (copy-on-write)
max_requests    = 1000          # restart worker après N requêtes (évite les fuites mémoire)
max_requests_jitter = 100       # ±100 pour éviter le restart simultané de tous les workers

# ── Logs ─────────────────────────────────────────────────────────────────────
loglevel        = "warning"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(L)s'
errorlog        = "-"           # stderr
accesslog       = "-"           # stdout

# ── Graceful shutdown ────────────────────────────────────────────────────────
proc_name       = "coderoute-backend"
