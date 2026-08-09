# ── Build stage ────────────────────────────────────────────────────
FROM python:3.12-slim AS build

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN apt-get update -q && apt-get install -y -q --no-install-recommends \
    build-essential libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ── Runtime stage ──────────────────────────────────────────────────
FROM python:3.12-slim AS runtime

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

RUN apt-get update -q && apt-get install -y -q --no-install-recommends \
    libpq5 curl postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copier les dépendances installées du stage build
COPY --from=build /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=build /usr/local/bin /usr/local/bin

# Copier le code source (sans tests, sans cache)
COPY app/ ./app/
COPY alembic/ ./alembic/
COPY alembic.ini .
COPY requirements.txt .
COPY gunicorn.conf.py .
COPY entrypoint.sh .
COPY scripts/ ./scripts/

# Utilisateur non-root pour la sécurité
RUN chmod 0755 entrypoint.sh scripts/*.sh \
    && useradd -m -u 1001 appuser \
    && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# Liveness pure : DB/Redis sont vérifiés par /health/readiness.
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=5 \
    CMD curl -sf http://localhost:8000/health/live || exit 1

# Entrypoint : en production P10, migrations/seeds sont sortis du startup.
CMD ["./entrypoint.sh"]
