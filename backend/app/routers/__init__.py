"""Initialisation des routeurs CodeRoute.

Le dashboard institutionnel agrège ici les contrôles de readiness v2 afin de
les exposer sous le même espace `/api/v1/dashboard` sans modifier le bootstrap
FastAPI principal.
"""
from app.routers import dashboard as dashboard
from app.routers import national_readiness as national_readiness

# Endpoint final : /api/v1/dashboard/national-readiness
# L'initialisation du package n'a lieu qu'une fois par processus Python.
dashboard.router.include_router(national_readiness.router)
