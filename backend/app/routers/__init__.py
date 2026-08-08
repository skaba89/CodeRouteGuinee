"""Initialisation des routeurs CodeRoute.

Les sous-routeurs spécialisés sont agrégés ici afin de conserver des espaces
API cohérents sans alourdir le bootstrap FastAPI principal.
"""
from app.routers import dashboard as dashboard
from app.routers import national_readiness as national_readiness

# Endpoint final : /api/v1/dashboard/national-readiness
# L'initialisation du package n'a lieu qu'une fois par processus Python.
dashboard.router.include_router(national_readiness.router)

# Center Edge : le protocole Offline Lease reste un sous-espace du routeur
# de confiance `/api/v1/center-edge`.
from app.routers import center_edge as center_edge
from app.routers import center_edge_offline as center_edge_offline

center_edge.router.include_router(center_edge_offline.router)
