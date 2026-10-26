# Stratégie de tests production

> Audit du 26 octobre 2026 — base `main` `2b4e9b809ff27ed9111bc51c074e599e166b1793`. Lecture seule des données et du code applicatif ; fichiers d’audit uniquement. Aucune connexion à une base de production, aucun déploiement, aucune fusion.

## Ce qui existe déjà

Pytest large sur SQLite avec couverture minimale 80 % en CI ; tests santé séparés. Fullstack Business E2E installe PostgreSQL 16, exécute Alembic, les invariants métier et un navigateur réel. Un test candidat multi-thread PostgreSQL existe : ne pas prétendre que tout PostgreSQL ou toute concurrence manque. Les specs Playwright majoritairement mockées vérifient UI/bridges, sans prouver le provider, la DB ou la PWA (Service Workers bloqués).

## Matrice prioritaire à ajouter / renforcer

| Priorité | Scénario | Dispositif et assertions |
|---|---|---|
| P0 | Production avec mode paiement absent/sandbox/invalide | Subprocess sans secret réel ; aucun appel sandbox/provider ; aucun paid ni booking réglé |
| P0 | Édition de question entre démarrage et soumission | DB migrée ; texte/options/correction/média modifiés depuis admin ; score et copie de tentative doivent rester ceux du démarrage |
| P0 | Deux démarrages simultanés même réservation | Deux connexions et workers, barrière avant décision ; une tentative/trace officielle, reprise déterministe |
| P0 | Save vs submit vs timeout simultanés | Barrières transactionnelles PostgreSQL ; une finalisation, un seul incrément attempt_count, réponses tardives refusées |
| P0 | Crash après acceptation fournisseur, avant commit local | Stub fournisseur comptant les effets, kill contrôlé worker ; retry même clé, un encaissement, état unknown rapprochable |
| P0 | Deux paiements concurrents et webhook concurrent | Multi-connexion ; un effet provider, montant serveur inchangé, unicité référence externe/événement, pas de deadlock non géré |
| P1 | Inter-centre et rattachement e-mail | Candidat A/B, centre A/B, auto-école A/B, admin ; lecture/écriture/export/QR/runtime ; adresse seule ne doit pas transférer de dossier |
| P1 | Replay refresh et révocation | Mot de passe changé, logout, désactivation, MFA ; vieux refresh refusé après rotation et détection réutilisation |
| P1 | Callback forgé/rejoué/incomplet | Mauvais montant/devise/bénéficiaire, référence inconnue, ordre inversé ; rapprochement via contrat fournisseur |
| P1 | Remboursement à quatre yeux simultané | Initiateur différent décideur ; deux completions, référence preuve dupliquée ; pas de double remboursement ni perte d’audit |
| P1 | Réservation de dernière place | N requêtes multi-worker, isolation PostgreSQL ; capacité jamais dépassée, pas de référence dupliquée |
| P1 | Upgrade d’ancienne base | Fixtures par révision, données anonymisées, Alembic upgrade sans reset ; diff modèle/DB, contraintes, index, timezone |
| P1 | Restore isolé et PITR | Dump production autorisé/anonymisé, clés/médias ; intégrité HMAC, documents et parcours API ; RPO/RTO mesurés |
| P1 | Coupure et reprise Edge | WAN coupé, perte secteur, horloge modifiée, certificat expiré, version rollback ; aucun résultat falsifié, sync idempotente |
| P2 | Accessibilité et PWA | axe, lecteur d’écran, clavier, zoom 200 %, contraste, Android faible gamme ; vraie PWA dans suite dédiée |
| P2 | Charge progressive | Arrivées aux horaires de session, autosaves, génération PDF, reporting, provider lent ; p95/p99, erreurs et saturation DB |

## Exécution sûre

Créer exclusivement des bases jetables au nom explicite ; vérification hôte/nom avant toute fixture qui nettoie des tables. `backend/tests/conftest.py` supprime des questions après chaque test : ne jamais pointer cette suite sur une base métier. Aucun DROP/TRUNCATE/restore ne doit viser production. Les scénarios CI qui recréent coderoute_e2e restent confinés au service PostgreSQL éphémère.

Réserver des suites PostgreSQL non parallélisées au niveau base, paralléliser explicitement les acteurs à l’intérieur des tests de concurrence. Forcer connexions distinctes, temps bornés et vérification des lignes persistées ; un mock de with_for_update ne prouve aucun verrou. Inclure AUDIT_CHAIN_ENABLED activé pour certains parcours production, la CI fullstack courante le désactive.

## Qualité des résultats et gates

Conserver logs, versions, SHA, commandes, codes retour, tests ignorés et exclusions. Ne pas annoncer un pourcentage couverture si la collecte n’a pas abouti. Les tests UI historiques exclus de la CI sont une dette visible, pas une validation. Un échec de setup est distingué d’un échec d’assertion métier.

Critères release : tous les parcours critiques verts sur PostgreSQL + navigateur réel ; tests de crash/concurrence et restore attestés ; dépendances triées ; aucune régression rôles/banque ; homologation DNTT ; approbation humaine. Les tests qui ne font que refléter l’implémentation n’ajoutent pas de preuve d’intégrité.
