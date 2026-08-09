# P11 — Security Go-Live Gate

## Objectif

`GET /api/v1/operations/security/status` distingue désormais :

1. l'état instantané du SOC (`status`) ;
2. les contrôles explicites de mise en service nationale (`go_live`).

Le but est d'empêcher qu'une chaîne HMAC valide soit interprétée comme une preuve suffisante de SOC national alors que l'OTLP, le WAF ou le SIEM restent dormants.

## Contrôles obligatoires

`go_live.ready=true` exige simultanément :

- `SOC_ENABLED=true` ;
- `AUDIT_CHAIN_ENABLED=true` ;
- chaîne audit HMAC valide ;
- `OTEL_TRACES_ENABLED=true` avec endpoint configuré ;
- `WAF_REQUIRED=true` et `WAF_PROVIDER` configuré ;
- `SIEM_REQUIRED=true` ;
- aucun signal sécurité actif au moment du snapshot.

Chaque contrôle expose `passed`, `code` et `detail`. Les contrôles en échec sont listés dans `go_live.blockers`.

## Ce que ce gate ne prouve pas

Les flags sont activés uniquement **après** recette externe. Même `go_live.ready=true` ne remplace pas :

- la preuve d'ingestion réelle des deux instances dans le SIEM ;
- la rétention, le RBAC et la recherche/corrélation SIEM ;
- la preuve du collector OTLP privé et l'audit d'absence de PII ;
- la preuve que le domaine passe réellement par le WAF et que l'origine n'est pas contournable ;
- les tests WAF bénins autorisés ;
- les exercices d'alerting, charge, chaos et incident ;
- les sign-offs technique, exploitation, sécurité et DNTT/métier.

Ces éléments restent listés dans `go_live.external_evidence_still_required` et dans l'issue #138.

## Séquence d'activation recommandée

1. Terminer la recette P10.2 / #134 ou faire accepter formellement les écarts.
2. Provisionner les clés SOC/HMAC dans le coffre.
3. Activer SOC + audit HMAC en staging et vérifier la chaîne.
4. Provisionner OTLP/SIEM/WAF, réaliser les recettes externes et archiver les preuves.
5. Passer les flags `OTEL_TRACES_ENABLED`, `SIEM_REQUIRED`, `WAF_REQUIRED` uniquement lorsque les composants associés sont prouvés.
6. Vérifier `/api/v1/operations/security/status` et exiger `go_live.ready=true`.
7. Relancer le Go-Live Evidence Pack et archiver le snapshot + SHA-256.
8. Réaliser le sign-off humain avant production nationale.

Aucun script de ce dépôt n'active automatiquement WAF, SIEM ou SOC en production.