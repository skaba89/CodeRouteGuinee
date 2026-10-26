# Audit de préparation production

> Audit du 26 octobre 2026 — base `main` `2b4e9b809ff27ed9111bc51c074e599e166b1793`. Lecture seule des données et du code applicatif ; fichiers d’audit uniquement. Aucune connexion à une base de production, aucun déploiement, aucune fusion.

## Décision

**NO-GO pour un examen institutionnel en production.** Base fonctionnelle riche, mais quatre blocages P0 : notation mutable, simulation de paiement possible en environnement production, seed pilote non protégé et instance publiée non prête lors du dernier contrôle consulté. Voir SECURITY_FINDINGS.md pour preuves, impacts et corrections.

Ce document complète l’audit historique AUDIT_EXISTANT.md ; les constats périmés de cet audit ne sont pas repris comme acquis. Les seeds génériques sont désormais bloqués en production et l’URL PDF utilise public_app_url. La CI contient déjà un parcours PostgreSQL réel. Les valeurs réglementaires ne sont pas homologuées par cet audit.

## Périmètre et méthode

Inventaire intégral des 861 chemins suivis, analyse AST des 442 fichiers Python, 275 déclarations de routes (avant remplacement des façades), 1350 fonctions de test Python au total, 20 workflows, 17 migrations. L’inventaire détaillé est dans evidence/source_inventory.json. Ces nombres ne sont ni des endpoints effectifs distincts ni des tests tous exécutés avec succès.

Revue approfondie des flux auth, autorisation dossier/centre, agrégation des routes, moteur et runtime examen, trace, banque, paiements/webhooks/remboursements, schéma/migrations, navigateur/PWA et chaîne exploitation. Les autres modules ont été inventoriés et contrôlés par les outils ; il ne s’agit pas d’une preuve de revue manuelle exhaustive ligne à ligne des 861 fichiers ni d’un pentest complet. Les fichiers environnement réels et banques importées privées ne sont pas lus.

Historique récent consulté : PR #255 suite backend bloquante ; #257 instructions et skills ; #258 durcissement seeds génériques ; #259 documentation d’audit. Aucun README n’est utilisé comme preuve suffisante d’opérationnalité.

## Architecture constatée

- Backend monolithe modulaire FastAPI, SQLAlchemy synchrone, Pydantic, Alembic ; PostgreSQL en exploitation, SQLite dans la majorité des tests. Métier par routeurs et services, avec plusieurs remplacements de routes et fonctions dans app/routers/__init__.py : auditer les façades effectivement montées, pas seulement les fonctions historiques.
- Frontend React 19, TypeScript 6, Vite 8, PWA Workbox ; interfaces candidat, centre, auto-école, administration et pilotage national. Application mobile limitée à configuration/stores dans mobile/, pas de parcours mobile natif complet prouvé.
- Agent Edge Python séparé : baux signés, journal hors ligne, mise à jour et trust store ; tests root partiellement cassés. Validation terrain non réalisée.
- Redis/distributed, audit HMAC, OpenTelemetry, Prometheus, Sentry, outils backup/PITR et preuves go-live présents. Leur configuration effective et leur exploitation continue ne sont pas déduites des fichiers.
- Autorisation applicative par rôle et périmètre centre. Aucune politique RLS PostgreSQL trouvée dans les migrations : ce n’est pas une architecture multi-tenant isolée par la base. L’absence de RLS n’est pas en elle-même une preuve de fuite ; les gardes applicatifs sont critiques.

## Contrôles exécutés

Voir evidence/RESULTS.md pour commandes et résultats finaux, ainsi que les sorties brutes adjacentes. Tous les tests locaux utilisent des bases éphémères. Les résultats CI sont signalés séparément.

## Preuves CI et exploitation

- CI du SHA audité : succès, run https://github.com/skaba89/CodeRouteGuinee/actions/runs/40208435112.
- Fullstack Business E2E au parent applicatif 29ace54 : succès, run https://github.com/skaba89/CodeRouteGuinee/actions/runs/40207103531. Le HEAD suivant fusionne de la documentation ; ce succès n’est pas présenté comme une nouvelle exécution locale.
- Verify Render Media Deployment : échec, run https://github.com/skaba89/CodeRouteGuinee/actions/runs/40271492015, job 121405080091. À 04:55 UTC : liveness 200 ; readiness 503/configuration ; SHA publié 4fa5291b0febc1714336e4eb7899160aa74d01df. Les contrôles du pack média passent ; leur succès ne prouve pas le décodage complet des médias ni une homologation.

## Risques transverses

Les verrous FOR UPDATE et advisory locks existent réellement, mais les échecs entre effet externe et commit restent possibles. L’audit HMAC détecte des altérations et impose append-only via ORM ; il ne remplace ni droits DB restreints, ni archivage externe, ni sauvegardes des clés.

Les certificats PDF et leur vérification publique sont implémentés. Le vérificateur reconnaît une tentative submitted, y compris un résultat failed : valid signifie authenticité du relevé, pas réussite au permis. Pas de preuve de signature institutionnelle du PDF ni d’objet certificat immuable avec révocation. Décisions de validité et publication à cadrer avec DNTT.

## Limites et critères de sortie

Pas de pentest réseau, de recette de fournisseur financier, de vérification de comptes production, de restauration production, de charge nationale, de matériel Edge ni d’évaluation WCAG complète. PostgreSQL local et Playwright restent soumis aux limites documentées dans les résultats ; ne pas remplacer leurs preuves par une suite SQLite verte.

Sortie : zéro P0 ouvert, scénarios PostgreSQL concurrentiels et financiers verts, restore isolé mesuré, readiness et SHA conformes, homologation des règles/contenus et acceptation DNTT, promotion explicitement validée. Aucun déploiement national en une seule étape.
