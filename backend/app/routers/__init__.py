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
from app.routers import media_migration_plan as media_migration_plan
from app.routers import media_official_readiness as media_official_readiness

media_library.router.include_router(media_migration_progress.router)
media_library.router.include_router(media_migration_queue.router)
media_library.router.include_router(media_migration_plan.router)
media_library.router.include_router(media_official_readiness.router)

# Le chemin manuel d'association doit partager la même clé de sérialisation
# (verrou sur Question) que le batch migrator. Le remplacement est fail-closed :
# si le contrat historique change, le démarrage échoue au lieu de laisser deux
# implémentations concurrentes actives.
from app.routers import media_link_guard as media_link_guard

_media_link_path = "/media-library/questions/{question_id}/links"
_legacy_media_link_routes = [
    route
    for route in media_library.router.routes
    if getattr(route, "path", None) == _media_link_path
    and "POST" in (getattr(route, "methods", set()) or set())
]
if len(_legacy_media_link_routes) != 1:
    raise RuntimeError(
        f"Expected exactly one legacy POST {_media_link_path} route, found {len(_legacy_media_link_routes)}"
    )

media_library.router.routes[:] = [
    *media_link_guard.router.routes,
    *[route for route in media_library.router.routes if route not in _legacy_media_link_routes],
]

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

# Éligibilité examen : les deux points de démarrage historiques sont remplacés
# par une façade qui revalide le dossier candidat. Le reste du moteur d'examen
# (trace, station, scoring, incident, certificat) reste strictement inchangé.
from app.routers import exam_start_eligibility_guard as exam_start_eligibility_guard

_exam_start_guard_specs = (
    ("/exams/start", "POST"),
    ("/exams/start-from-booking", "POST"),
)
_legacy_exam_start_routes = []
for _path, _method in _exam_start_guard_specs:
    _matches = [
        route
        for route in exams.router.routes
        if getattr(route, "path", None) == _path
        and _method in (getattr(route, "methods", set()) or set())
    ]
    if len(_matches) != 1:
        raise RuntimeError(
            f"Expected exactly one legacy {_method} {_path} route, found {len(_matches)}"
        )
    _legacy_exam_start_routes.extend(_matches)

exams.router.routes[:] = [
    *exam_start_eligibility_guard.router.routes,
    *[
        route
        for route in exams.router.routes
        if route not in _legacy_exam_start_routes
    ],
]

# Soumission manuelle : une tentative active ne peut être finalisée que lorsque
# chaque question de la trace officielle possède une réponse effective. La
# façade fusionne la dernière autosauvegarde serveur avec le payload final puis
# délègue au moteur historique. Le timeout automatique reste totalement séparé.
from app.routers import exam_submit_completion_guard as exam_submit_completion_guard

_exam_submit_path = "/exams/{attempt_id}/submit"
_legacy_exam_submit_routes = [
    route
    for route in exams.router.routes
    if getattr(route, "path", None) == _exam_submit_path
    and "POST" in (getattr(route, "methods", set()) or set())
]
if len(_legacy_exam_submit_routes) != 1:
    raise RuntimeError(
        f"Expected exactly one legacy POST {_exam_submit_path} route, found {len(_legacy_exam_submit_routes)}"
    )

exams.router.routes[:] = [
    *exam_submit_completion_guard.router.routes,
    *[route for route in exams.router.routes if route not in _legacy_exam_submit_routes],
]

# Nouvelle tentative officielle : le moteur historique conserve tout son contrat,
# mais sa fonction de création est remplacée par une implémentation qui filtre la
# banque sur le média réellement publiable. Une question normalisée devenue
# invalide ne peut donc pas retomber silencieusement vers un ancien média legacy.
from app.official_exam_attempt_service import create_media_safe_exam_attempt

exams._create_exam_attempt = create_media_safe_exam_attempt

# Paiements : cotation serveur + dispatcher fail-closed. POST /payments est
# remplacé par une façade idempotente qui utilise la réservation comme clé
# métier, persiste les checkout URLs asynchrones et refuse un second débit sur
# un état paid/checked_in incohérent.
from app.routers import payments as payments
from app.routers import payment_quote as payment_quote
from app.routers import payment_create_guard as payment_create_guard
from app.payment_provider_dispatcher import dispatch_mobile_money_payment

payments.router.include_router(payment_quote.router)
payments.simulate_mobile_money_payment = dispatch_mobile_money_payment

_payment_create_path = "/payments"
_legacy_payment_create_routes = [
    route
    for route in payments.router.routes
    if getattr(route, "path", None) == _payment_create_path
    and "POST" in (getattr(route, "methods", set()) or set())
]
if len(_legacy_payment_create_routes) != 1:
    raise RuntimeError(
        f"Expected exactly one legacy POST {_payment_create_path} route, found {len(_legacy_payment_create_routes)}"
    )

payments.router.routes[:] = [
    *payment_create_guard.router.routes,
    *[
        route
        for route in payments.router.routes
        if route not in _legacy_payment_create_routes
    ],
]

# Compatibilité réservation : les anciens clients peuvent encore appeler
# /registration/availability et /registration/book. Ces deux routes historiques
# sont remplacées par une façade qui applique exactement les invariants
# transactionnels de /bookings/self. Le remplacement est fail-closed pour éviter
# qu'une évolution future laisse deux implémentations concurrentes actives.
from app.routers import registration as registration
from app.routers import registration_booking_guard as registration_booking_guard

_registration_guard_specs = (
    ("/registration/availability", "GET"),
    ("/registration/book", "POST"),
)
_legacy_registration_booking_routes = []
for _path, _method in _registration_guard_specs:
    _matches = [
        route
        for route in registration.router.routes
        if getattr(route, "path", None) == _path
        and _method in (getattr(route, "methods", set()) or set())
    ]
    if len(_matches) != 1:
        raise RuntimeError(
            f"Expected exactly one legacy {_method} {_path} route, found {len(_matches)}"
        )
    _legacy_registration_booking_routes.extend(_matches)

registration.router.routes[:] = [
    *registration_booking_guard.router.routes,
    *[
        route
        for route in registration.router.routes
        if route not in _legacy_registration_booking_routes
    ],
]

# Création candidat : toutes les routes qui fabriquent une référence GN-CODE-*
# partagent désormais le même advisory lock PostgreSQL. L'inscription publique
# et auto-école utilisent aussi le même contrôle identité/téléphone normalisé.
from app.routers import candidates as candidates
from app.candidate_creation_rules import (
    assert_candidate_identity_phone_unique,
    build_candidate_reference_locked,
)

candidates.build_candidate_reference = build_candidate_reference_locked
registration.build_candidate_reference = build_candidate_reference_locked
registration._check_duplicates = assert_candidate_identity_phone_unique

# Mise à jour candidat : le PATCH historique acceptait n'importe quelle chaîne
# comme statut. La façade contrôlée conserve les champs profil mais réserve
# `verified` au workflow d'identité et exige un motif pour les changements
# administratifs registered/suspended.
from app.routers import candidate_update_guard as candidate_update_guard

_candidate_update_path = "/candidates/{candidate_id}"
_legacy_candidate_update_routes = [
    route
    for route in candidates.router.routes
    if getattr(route, "path", None) == _candidate_update_path
    and "PATCH" in (getattr(route, "methods", set()) or set())
]
if len(_legacy_candidate_update_routes) != 1:
    raise RuntimeError(
        f"Expected exactly one legacy PATCH {_candidate_update_path} route, found {len(_legacy_candidate_update_routes)}"
    )

candidates.router.routes[:] = [
    *candidate_update_guard.router.routes,
    *[
        route
        for route in candidates.router.routes
        if route not in _legacy_candidate_update_routes
    ],
]
