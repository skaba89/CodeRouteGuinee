# Constats de sécurité et intégrité

> Audit du 26 octobre 2026 — base `main` `2b4e9b809ff27ed9111bc51c074e599e166b1793`. Lecture seule des données et du code applicatif ; fichiers d’audit uniquement. Aucune connexion à une base de production, aucun déploiement, aucune fusion.

P0 : bloque la production institutionnelle ; P1 : à lever avant pilote réel ; P2 : amélioration avant généralisation. Les constats conditionnels et preuves opérationnelles manquantes ne sont pas présentés comme des exploitations avérées.

## EX-01 — P0 — Clé de notation mutable après démarrage

- Fichier / preuve : `backend/app/routers/exams.py:637` ; `backend/app/routers/exam_runtime.py:193` ; `backend/app/routers/questions.py:133`.
- Constat vérifiable : Les soumissions manuelle et timeout relisent Question.correct_answer. L’import réécrit une question existante sans révision immuable et sans invalider son approbation.
- Impact : Une modification administrative peut modifier la notation d’une épreuve en cours ; un hash historique ne reconstruit pas le contenu.
- Correctif recommandé : Révisions immuables texte/options/correction/médias/règles, références dans la trace ; ne pas recalculer les résultats historiques. Garde conservatoire sur modifications de questions déjà utilisées à étudier.

## PAY-01 — P0 — Paiement simulé accepté dans un environnement production

- Fichier / preuve : `backend/app/payment_provider_dispatcher.py:138` ; `backend/app/core/config.py:70` ; `render.yaml:191`.
- Constat vérifiable : Reproduction isolée : validate_production_secrets accepte sandbox ; sans MOBILE_MONEY_MODE, dispatcher wave retourne paid sans appel fournisseur. Le Blueprint configure sandbox.
- Impact : Une configuration déployable peut déclarer réglée une réservation sans encaissement réel. Condition : production avec mode sandbox/absent/invalide.
- Correctif recommandé : Distinguer environnement de déploiement et mode fournisseur ; refuser toute simulation en production au démarrage ET au dispatcher. Configurer les pilotes simulés hors production. Tests de non-régression.

## SEC-01 — P0 — Seed pilote sans garde production

- Fichier / preuve : `backend/app/seed_pilote_conakry.py:109` ; `backend/app/seed_pilote_conakry.py:44`.
- Constat vérifiable : run ouvre SessionLocal directement ; mot de passe centre de secours connu et données fictives ; la doc du module vise une base de production. Le garde seed_full.run n’est pas appelé par seed_questions.
- Impact : Création possible d’un compte centre connu et de dossiers/réservations fictifs si le script est exécuté. Existence de ce compte en production non vérifiée.
- Correctif recommandé : Bloquer le seed pilote en production avant toute session DB ; conserver le provisionnement réel via procédure contrôlée. Vérifier hors bande les comptes déjà créés, sans purge automatique.

## OPS-01 — P0 — Readiness de l’instance publiée en échec

- Fichier / preuve : `GitHub Actions 40271492015 / job 121405080091`.
- Constat vérifiable : Le 26/10/2026 à 04:55 UTC : /health/readiness HTTP 503, configuration bloquante ; commit publié 4fa5291b… au lieu de 2b4e9b8…. Liveness 200. Médias du pack contrôlé : contrôles verts.
- Impact : Pas de preuve qu’une version saine et conforme soit actuellement exploitable. Observation datée, non un diagnostic permanent.
- Correctif recommandé : Diagnostiquer la configuration et la promotion avec l’exploitant ; recette puis promotion manuelle après readiness et SHA exact. Ne pas déployer dans cet audit.

## SEC-02 — P1 — Autorisation de dossier par e-mail sans preuve de possession

- Fichier / preuve : `backend/app/resource_access.py:35` ; `backend/app/routers/candidates.py:71` ; `backend/app/routers/auth.py:60`.
- Constat vérifiable : Reproduction SQLite : candidate.user_id=owner et candidate.email=actor.email ; assert_candidate_access autorise actor, et /me renvoie le dossier. L’inscription générique ne vérifie pas la possession de l’adresse.
- Impact : Accès horizontal possible si un dossier porte une adresse revendiquée par un autre compte. Même fallback dans paiements et runtime.
- Correctif recommandé : Rattachement explicite par user_id ; procédure vérifiée pour les dossiers historiques ; matrice IDOR candidate/centre/auto-école. Ne pas réattribuer massivement les données.

## SEC-03 — P1 — Refresh et accès non révocables individuellement

- Fichier / preuve : `backend/app/security.py:43` ; `backend/app/routers/auth.py:191`.
- Constat vérifiable : Pas de jti/token_version ni de consommation du refresh précédent ; changement de mot de passe sans invalidation des jetons existants.
- Impact : Persistance d’un accès volé jusqu’à expiration ; refresh réutilisable. La désactivation du compte est bien contrôlée à chaque accès.
- Correctif recommandé : Sessions révocables, refresh tournant et détection de réutilisation ; migration additive et compatibilité contrôlée.

## SEC-04 — P1 — Jetons navigateur persistés et MFA facultative

- Fichier / preuve : `frontend/src/authClient.ts:52` ; `backend/app/routers/auth.py:123`.
- Constat vérifiable : Access et refresh dans localStorage ; le login délivre des jetons sans MFA si elle n’est pas activée.
- Impact : Une XSS aurait accès aux jetons ; protection renforcée des comptes institutionnels non garantie. Aucune XSS exploitable démontrée ici.
- Correctif recommandé : Cookies HttpOnly adaptés aux domaines et CSRF, MFA obligatoire pour rôles sensibles après procédure d’enrôlement/récupération.

## PAY-02 — P1 — Fenêtre de double débit après effet externe non persisté

- Fichier / preuve : `backend/app/routers/payment_create_guard.py:148` ; `backend/app/routers/payment_create_guard.py:103`.
- Constat vérifiable : Le provider est appelé avant insertion/commit du Payment ; le verrou réservation sérialise les appels normaux mais un crash après création externe perd la référence locale. La clé d’idempotence métier n’est pas transmise au dispatcher.
- Impact : Un retry après crash/rollback peut créer un deuxième paiement chez le fournisseur. Non reproduit sur fournisseur réel.
- Correctif recommandé : Intention persistée avant appel, clé fournisseur stable, états initiating/unknown/pending, rapprochement et outbox ; tests de fault injection.

## PAY-03 — P1 — Webhook permissif sur montant absent et validation fournisseur partielle

- Fichier / preuve : `backend/app/routers/payments.py:99` ; `backend/app/payment_webhook_security.py:96`.
- Constat vérifiable : Montant absent accepté ; PayDunya vérifie un hash statique de clé, pas une signature liée aux champs de transaction. Aucune consultation fournisseur avant passage paid dans ce callback.
- Impact : Le callback est une preuve d’encaissement incomplète ; risque si payload authentifié réutilisé/altéré. Signature Wave présente avec fenêtre temporelle.
- Correctif recommandé : Confirmer les contrats fournisseurs, vérifier référence/montant/devise/bénéficiaire via API de confirmation et journaliser un identifiant événement unique. Pas de changement d’algorithme signé sans contrat.

## DEP-01 — P1 — Dépendances Python signalées vulnérables

- Fichier / preuve : `backend/requirements.txt:1` ; `docs/audit/evidence/pip-audit.json`.
- Constat vérifiable : pip-audit retourne 66 entrées sur 8 paquets, soit 46 couples paquet/avis distincts après dédoublonnage. Inclut python-jose, cryptography, python-multipart, pypdf, pytest, opentelemetry-api, starlette et ecdsa.
- Impact : Exposition potentielle dépendante des chemins utilisés ; aucune exploitation ne découle automatiquement du nombre d’avis.
- Correctif recommandé : Trier chaque avis, dépendances runtime/dev et atteignabilité ; mise à niveau cohérente FastAPI/Starlette et JWT, tests et nouvel audit. Ne pas déclarer 66 CVE uniques.

## EX-02 — P1 — Banque publique de démonstration et absence de preuve de banque homologuée

- Fichier / preuve : `backend/app/question_bank_gn.py:19` ; `backend/app/exam_engine.py:70`.
- Constat vérifiable : Le dépôt contient les questions et corrections de démonstration. Le filtre exclut le dataset training historique, pas une empreinte de toute banque de démo publique.
- Impact : Ces contenus ne peuvent pas constituer une banque confidentielle d’examen. La banque réellement importée en production est inconnue.
- Correctif recommandé : Banque DNTT privée, contrôles d’import/homologation et distinction explicite démo/officiel. Valider taille et répartition avec DNTT.

## EX-03 — P1 — Paramètres et publication non versionnés par tentative

- Fichier / preuve : `backend/app/exam_engine.py:28` ; `backend/app/routers/exams.py:654`.
- Constat vérifiable : 40 questions, 35/40 et 30 minutes dans le code ; soumission rend score/résultat disponible. Pas de jeu de règles historisé lié à la tentative.
- Impact : Difficulté de justifier la règle applicable et de traiter les recours après évolution. Une publication différée n’est pas présentée comme une obligation juridique acquise.
- Correctif recommandé : Versionner le comportement actuel comme provisoire ; décisions DNTT pour publication, multi-réponses, pauses et seuils. Aucune règle changée dans cette PR.

## EX-04 — P1 — Finalisation et notifications dépendantes du client

- Fichier / preuve : `backend/app/routers/exam_runtime.py:162` ; `backend/app/routers/exams.py:698`.
- Constat vérifiable : Timeout finalise sur requête ; notifications best effort dans soumission. Pas de worker de finalisation d’examen identifié dans scheduled_notifications.
- Impact : Tentative abandonnée non finalisée sans client ; notification perdue après incident. Le chrono continue pendant les coupures.
- Correctif recommandé : Worker idempotent, reprise et outbox transactionnelle ; pause éventuelle sur décision DNTT, jamais ajout de temps implicite.

## DB-01 — P1 — Migrations initiales couplées aux modèles courants

- Fichier / preuve : `backend/alembic/versions/20260617_0001_initial_schema.py:22`.
- Constat vérifiable : Migration initiale importe les modèles du HEAD ; ses effets varient avec les évolutions. Une tête 0017 et aller depuis base vide SQLite vérifiés.
- Impact : Une reconstruction vierge peut masquer des colonnes manquantes lors d’une montée depuis une ancienne base. PostgreSQL local non exécuté.
- Correctif recommandé : DDL initial figé après stratégie de compatibilité approuvée ; tests upgrade depuis sauvegardes anonymisées de chaque révision et comparaison contraintes/index/types.

## QA-01 — P1 — Tests de concurrence examen et crash financier insuffisamment démontrés

- Fichier / preuve : `backend/tests/test_candidate_creation_concurrency.py:86` ; `.github/workflows/fullstack-business-e2e.yml:97`.
- Constat vérifiable : La CI exécute réellement PostgreSQL et un test de concurrence de références candidats. Les tests runtime/paiement consultés ne lancent pas de requêtes financières ou de soumissions réellement simultanées par barrière multi-connexion.
- Impact : SQLite ne prouve ni FOR UPDATE, ni deadlocks, ni absence de double effet après crash.
- Correctif recommandé : Ajouter scénarios PostgreSQL multi-worker décrits dans TEST_STRATEGY ; conserver le parcours fullstack existant et ses gardes.

## EDGE-01 — P1 — Suite de confiance Edge en échec

- Fichier / preuve : `edge_agent/tests/test_release_trust.py:64` ; `docs/audit/evidence/edge-tests.txt`.
- Constat vérifiable : 41 passed, 3 failed ; verify_staged_release_for_root exige expected_node_id, expected_center_id et expected_current_version, omis par les trois tests.
- Impact : La chaîne de livraison Edge n’a pas une suite locale intégralement verte ; le test ne vérifie plus son scénario attendu.
- Correctif recommandé : Adapter fixtures et cas négatifs au nouveau contrat, sans rendre les arguments optionnels ni affaiblir la vérification root.

## OPS-02 — P1 — Promotion de main automatique

- Fichier / preuve : `render.yaml:19`.
- Constat vérifiable : Le Blueprint utilise checksPass sur main ; le dépôt ne prouve pas l’état effectif des protections administratives GitHub ni des réglages Render actuels.
- Impact : Une fusion peut déclencher une publication sans décision d’exploitation explicite.
- Correctif recommandé : Préproduction et promotion manuelle de l’artefact testé avec validation humaine ; revoir protections de branche avec les droits administratifs adaptés.

## DR-01 — P1 — Restauration de production non démontrée

- Fichier / preuve : `scripts/postgres_backup.py:104` ; `.github/workflows/backup.yml:71`.
- Constat vérifiable : Outils pg_dump/pg_restore, répétition CI éphémère, PITR et preuves existent. pg_restore --list vérifie une archive, pas le parcours applicatif restauré. Aucun PV de restauration de sauvegarde production consulté.
- Impact : RPO/RTO et récupération des clés/médias non prouvés sur environnement d’exploitation.
- Correctif recommandé : Exercice isolé, sauvegardes chiffrées hors compte principal, restauration DB+médias+clés, mesures RPO/RTO et procès-verbal signé.

## SEC-05 — P1 — Fichiers environnement suivis par Git

- Fichier / preuve : `.env.dev` ; `frontend/.env.local` ; `frontend/.env.production` (git ls-files).
- Constat vérifiable : Noms suivis identifiés ; contenu volontairement non lu conformément à CLAUDE.md.
- Impact : Possibilité d’exposition historique ; aucun secret effectif établi dans cet audit.
- Correctif recommandé : Revue humaine autorisée, retrait du suivi si nécessaire, rotation ciblée si secret avéré ; ne pas réécrire l’historique sans plan.

## UI-01 — P2 — Accessibilité et expérience en conditions réelles non validées

- Fichier / preuve : `frontend/src/pages/exam.tsx:768` ; `frontend/playwright.config.ts:21`.
- Constat vérifiable : Labels ARIA, commandes clavier, reprise et progression présents ; pas de résultat axe/lecteur d’écran/contraste consulté. Playwright bloque les Service Workers par configuration.
- Impact : La réussite du build ne prouve pas WCAG, accessibilité mobile, PWA et usage par candidats novices.
- Correctif recommandé : Recette clavier/lecteur d’écran/zoom, appareils et réseau faibles, axe en CI ; parcours PWA séparé et familiarisation validée avec DNTT.

## QA-02 — P2 — Dette statique non bloquante

- Fichier / preuve : `.github/workflows/ci.yml:26` ; `docs/audit/evidence/ruff.json` ; `docs/audit/evidence/mypy.txt`.
- Constat vérifiable : Ruff complet : 210 écarts ; sélection critique verte. mypy 2.4.0 installé pour audit : 98 erreurs dans 35 fichiers, 171 fichiers vérifiés avec ignore-missing-imports ; pas de configuration mypy projet trouvée.
- Impact : La CI peut rester verte malgré cette dette ; risque de régressions de types, imports et maintenabilité.
- Correctif recommandé : Baseline suivie et réduction progressive, verrouillage version/configuration mypy, corrections par domaine sans grand reformatage.

## PERF-01 — P2 — Agrégations globales en mémoire et verrous longs

- Fichier / preuve : `backend/app/routers/payments.py:265` ; `backend/app/routers/payment_create_guard.py:148`.
- Constat vérifiable : Synthèses chargent toutes les lignes ; verrou réservation conservé pendant I/O fournisseur ; pool et télémétrie existent mais pas de résultat de charge nationale exécuté ici.
- Impact : Mémoire/latence croissantes et contention sous pic d’inscriptions/paiements.
- Correctif recommandé : Agrégats SQL paginés, budgets pool par instance, appels asynchrones via intentions persistées, charge réaliste avant généralisation.
