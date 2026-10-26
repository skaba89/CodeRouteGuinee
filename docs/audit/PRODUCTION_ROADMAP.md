# Feuille de route et premier changement proposé

> Audit du 26 octobre 2026 — base `main` `2b4e9b809ff27ed9111bc51c074e599e166b1793`. Lecture seule des données et du code applicatif ; fichiers d’audit uniquement. Aucune connexion à une base de production, aucun déploiement, aucune fusion.

## Ordre de remédiation

| Lot / PR | Priorité et constats | Livrable | Critère d’acceptation |
|---|---|---|---|
| 0 — Bloquer les paiements simulés en production | P0 PAY-01 | Garde de démarrage et garde runtime indépendantes ; plan ci-dessous | Matrice env/mode + aucun appel sandbox en production ; suite financière verte |
| 1 — Fermer les seeds restants | P0 SEC-01 | Garde avant SessionLocal dans seed pilote ; tests subprocess et faux SessionLocal | Production bloque même avec override, aucun accès DB ; démo développement préservée |
| 2 — Stabiliser la copie et la correction | P0 EX-01 | Révisions immuables et référence versionnée dans trace ; plan de migration préalable | Édition banque pendant examen ne change ni questions ni score ; timeout/submit identiques |
| 3 — Assainir l’exploitation publiée | P0 OPS-01, P1 OPS-02 | Diagnostic configuration, préproduction, promotion manuelle | Readiness 200 et SHA exact, rollback répété, validation exploitant |
| 4 — Renforcer autorisations et sessions | P1 SEC-02/03/04/05 | Rattachement explicite, révocation, MFA, secrets | Matrice IDOR et session volée/révoquée testée |
| 5 — Sécuriser les effets financiers | P1 PAY-02/03 | Intentions persistées, clés stables, confirmation/inbox, rapprochement | Crash à chaque étape et callbacks concurrents sans double effet |
| 6 — Restaurer avant le pilote | P1 DR-01, DB-01 | Restore isolé, upgrade ancienne révision, sauvegarde clés/médias | RPO/RTO mesurés et acceptés ; aucun reset de base métier |
| 7 — Certifier examens et contenus | P1 EX-02/03/04, QA-01 | Homologation, worker échéances, parcours simultanés | Décisions DNTT et preuves intégrité multi-worker |
| 8 — Rendre les contrôles fiables | P1 DEP-01, EDGE-01 ; P2 QA-02 | Dépendances triées/mises à jour et tests Edge adaptés | Audit de dépendances retrié, suite Edge verte sans affaiblissement |
| 9 — Pilote puis généralisation | P2 UI-01, PERF-01 | Accessibilité, charge et terrain, déploiement par centres | Aucun P0/P1 non accepté ; PV pilote, astreinte et restauration validés |

Les lots sauvegardes, dépendances et préparation des décisions DNTT peuvent avancer en parallèle organisationnel. Les mises en production restent manuelles ; aucune date nationale ne peut être promise avant validation des critères.

## Première PR P0 préparée — PAY-01

**Statut : plan prêt à valider, code applicatif non modifié.** Branche prévue `fix/p0-production-payment-mode`. La PR d’audit n’est pas une PR corrigeant PAY-01 et ne doit pas être décrite comme telle.

### Fichiers et comportement proposé

1. `backend/app/core/config.py` : validation de démarrage refusant un mode autre que production si ENVIRONMENT=production ; erreur explicite sans secret.
2. `backend/app/payment_provider_dispatcher.py` : garde de défense en profondeur évaluant l’environnement effectif avant toute branche sandbox, pour bloquer même si le garde de démarrage a été contourné. Mode absent/invalide refuse l’encaissement ; aucun résultat paid simulé. Développement et test conservent leurs simulations.
3. Tests ciblés, par exemple `backend/tests/test_production_payment_mode.py` : production × mode absent/sandbox/invalide/production, ENVIRONMENT en casse variable, aucune invocation sandbox, contrat fail-closed sans API réelle. Couvrir le provider Celcom et les alias. L’API ne doit pas créer de paiement payé après refus.
4. `render.yaml` : changement de configuration uniquement après décision explicite sur le pilote. Proposition : mode production et clés fournies via secret store pour une vraie production ; une démo reste sur un environnement distinct. Ne pas activer un provider réel sans contrat et recette.
5. Fixtures de configuration production et documents de déploiement : adapter les exemples et tests qui comptaient implicitement sur sandbox. Lister les fichiers exacts après recherche de dépendances dans cette branche dédiée.

### Impacts et risques

Le déploiement d’une configuration production restée sandbox serait volontairement refusé. Le Blueprint actuel utilise ce mode : c’est une incompatibilité d’exploitation majeure à valider avant de toucher au code ou à la configuration. Aucun changement de prix, de remboursement, de rôle ni de règle d’examen ; aucune migration et aucun appel de débit dans les tests.

### Validation

Régression financière et sécurité, suite backend complète, PostgreSQL réel (replay et état booking), Ruff fichiers touchés, typecheck/build si contrat frontend impacté, audit dépendances. CI sur PR et recette manuelle isolée. Un test qui échoue par absence de navigateur ou PostgreSQL ne vaut pas validation.

### Retour arrière

Pas de rollback de données. Conserver les paiements existants, bloquer les nouveaux paiements si le mode n’est pas correctement configuré. Restaurer une version précédente seulement en environnement recette ; en production conserver le blocage des simulations plutôt que réintroduire une fausse confirmation. Ne pas reclasser rétroactivement des paiements sandbox sans rapprochement et décision métier.

## Validation requise avant implémentation

Le `CLAUDE.md` du dépôt, section Workflow, exige : « Changement important (examen, résultats, banque, auth, paiements, migration, CI/infra, nouvel endpoint, > 3 fichiers) : plan écrit (fichiers, impacts, risques, tests, rollback) → attendre un “OK” → implémentation ».

Le premier changement touche paiements et configuration de production : ce plan constitue le résultat concret à valider. Les documents d’audit demandés sont préparés ; aucun déploiement, aucune fusion et aucune modification applicative n’ont été effectués.
