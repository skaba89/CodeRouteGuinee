"""
Configuration Gunicorn pour CodeRoute Guinée — production.

Gunicorn comme process manager + Uvicorn workers :
  - Gunicorn gère le cycle de vie des workers (restart automatique, graceful reload)
  - UvicornWorker gère les connexions HTTP asynchrones
  - Chaque worker = un process Python indépendant

Le nombre de workers est borné en production via WEB_CONCURRENCY dans le
Blueprint afin de garder un budget PostgreSQL prévisible.
"""
import multiprocessing
import os

# ── Workers ──────────────────────────────────────────────────────────────────
_cpu_count   = multiprocessing.cpu_count()
workers      = int(os.getenv("WEB_CONCURRENCY", (2 * _cpu_count) + 1))
worker_class = "uvicorn.workers.UvicornWorker"

# ── Timeouts ─────────────────────────────────────────────────────────────────
timeout          = 60
graceful_timeout = 30
keepalive        = 5

# ── Connexions ────────────────────────────────────────────────────────────────
worker_connections = 1000

# ── Réseau ───────────────────────────────────────────────────────────────────
bind            = "0.0.0.0:8000"
backlog         = 2048

# ── Performance ──────────────────────────────────────────────────────────────
preload_app     = True
max_requests    = 1000
max_requests_jitter = 100

# ── Logs ─────────────────────────────────────────────────────────────────────
loglevel        = "warning"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(L)s'
errorlog        = "-"
accesslog       = "-"

# ── Graceful shutdown ────────────────────────────────────────────────────────
proc_name       = "coderoute-backend"


def child_exit(_server, worker) -> None:
    """Supprime les fichiers métriques d'un worker mort en mode multiprocess."""
    if not os.getenv("PROMETHEUS_MULTIPROC_DIR"):
        return
    from prometheus_client import multiprocess
    multiprocess.mark_process_dead(worker.pid)
