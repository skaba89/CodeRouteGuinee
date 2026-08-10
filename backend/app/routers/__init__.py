"""Initialisation des routeurs CodeRoute.

Les sous-routeurs spécialisés sont agrégés ici afin de conserver des espaces
API cohérents sans alourdir le bootstrap FastAPI principal.
"""
from app.routers import dashboard as dashboard
from app.routers import national_readiness as national_readiness

# Endpoint final : /api/v1/dashboard/national-readiness
# L'initialisation du package n'a lieu qu'une fois par processus Python.
dashboard.router.include_router(national_readiness.router)

# Center Edge : les gardes stricts sont montés AVANT leurs implémentations
# génériques afin que FastAPI résolve les routes sensibles par la version gardée.
from app.routers import center_edge as center_edge
from app.routers import center_edge_install_authorization_guard as center_edge_install_authorization_guard
from app.routers import center_edge_release as center_edge_release
from app.routers import center_edge_release_guard as center_edge_release_guard
from app.routers import center_edge_station_guard as center_edge_station_guard
from app.routers import center_edge_supply_chain as center_edge_supply_chain
from app.routers import center_edge_supply_chain_guard as center_edge_supply_chain_guard

center_edge.router.include_router(center_edge_station_guard.router)
# P9 doit intercepter le rollout avant le quality gate P8, puis déléguer vers lui.
center_edge.router.include_router(center_edge_supply_chain_guard.router)
center_edge.router.include_router(center_edge_release_guard.router)
# Chaque check éligible reçoit une autorisation d'installation centrale courte et
# signée. Le root updater la rafraîchit immédiatement avant la maintenance.
center_edge.router.include_router(center_edge_install_authorization_guard.router)
# P9 remplace aussi la vue de clé de signature par une réponse compatible P8
# enrichie d'un trousseau de rotation.
center_edge.router.include_router(center_edge_supply_chain.router)
center_edge.router.include_router(center_edge_release.router)

# Media : pilotage admin-only de la migration ajouté au routeur médiathèque
# existant afin d'éviter de multiplier les points de montage dans main.py.
from app.routers import media_library as media_library
from app.routers import media_migration_progress as media_migration_progress
from app.routers import media_migration_queue as media_migration_queue

media_library.router.include_router(media_migration_progress.router)
media_library.router.include_router(media_migration_queue.router)

# Media Phase 5 : remplace uniquement la lecture candidate des questions de
# l'examen officiel. Le routeur historique continue de porter score, soumission,
# timeout, certificats et gardes centre. Le remplacement est fail-closed : si la
# route historique change ou se duplique, le démarrage échoue au lieu de servir
# silencieusement le mauvais contrat média.
from app.routers import exams as exams
from app.routers import exam_media_guard as exam_media_guard

_exam_question_path = "/exams/{attempt_id}/questions"
_legacy_question_routes = [
    route
    for route in exams.router.routes
    if getattr(route, "path", None) == _exam_question_path
    and "GET" in (getattr(route, "methods", set()) or set())
]
if len(_legacy_question_routes) != 1:
    raise RuntimeError(
        f"Expected exactly one legacy GET {_exam_question_path} route, found {len(_legacy_question_routes)}"
    )

exams.router.routes[:] = [
    *exam_media_guard.router.routes,
    *[route for route in exams.router.routes if route not in _legacy_question_routes],
]
