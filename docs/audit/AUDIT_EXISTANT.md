# Audit de l'existant — CodeRoute Guinée

> Audit en lecture seule, réalisé le 25/10/2026 sur `main` @ `3b9318d`.
> Aucun fichier applicatif n'a été modifié. Les références `fichier:ligne`
> renvoient à ce commit.

## 1. Synthèse

CodeRoute Guinée est une base **solide sur la chaîne administrative** (inscription,
identité, réservation, paiement, contrôle d'entrée, traçabilité, audit chaîné,
supervision) et **en avance sur l'exploitation** (mode hors-ligne des centres,
HA, PITR, SOC). Le **cœur métier de l'examen reste au niveau démonstrateur** :

| Domaine | Verdict |
|---|---|
| Parcours administratif candidat | Implémenté et testé |
| Intégrité technique d'une tentative (trace, verrou, hash, audit) | Implémenté et testé |
| Moteur d'examen (questions, notation, règles) | **Partiel** : QCM à réponse unique, paramètres codés en dur |
| Banque de questions | **Insuffisante** : 40 questions officielles, publiques, sans média |
| Publication des résultats | **Absente** : résultat immédiat et notifié dès la soumission |
| Antifraude en salle | Partiel : registre de postes et passerelle edge, pas de détection côté poste |
| Sécurité applicative | Bonne base ; session JWT non révocable, 2FA non imposée, jetons en `localStorage` |
| CI/CD | Très fournie (20 workflows) ; la fusion dans `main` déclenche un déploiement Render |

**Conclusion** : la plateforme peut être **démontrée**, mais pas **exploitée pour
des examens officiels** tant que les points critiques C1 à C5 ne sont pas levés.

## 2. Risques classés par criticité

### Critiques (bloquants pour un examen officiel)

| # | Risque | Preuve |
|---|---|---|
| C1 | **Banque officielle publique et unique.** Les 40 questions officielles et leurs bonnes réponses sont dans le dépôt public (`backend/app/question_bank_gn.py`, `QUESTIONS_GN`). Le pool contient exactement les 40 questions de la répartition (10/6/5/5/4/4/3/3) : **tous les candidats reçoivent les mêmes questions**, seul l'ordre change. | `exam_engine.py:31-40`, `seed_full.py:2019-2051`. Comptage : 40 GN, 0 média, 0 traduction. |
| C2 | **Résultat publié sans contrôle.** Le score est calculé, enregistré et envoyé par e-mail, SMS et WhatsApp dans la même requête que la soumission. Il n'y a ni délai de publication, ni validation, ni gel avant recours. | `routers/exams.py:651-727` |
| C3 | **Réponse unique seulement.** `Question.correct_answer` est une chaîne et la notation compare deux chaînes. Les QCM à plusieurs bonnes réponses (modèle français) sont impossibles sans changer le modèle. La réponse est comparée au **texte** de l'option, si bien qu'une correction de libellé change la clé. | `models_question.py:20-21`, `exam_engine.py:score_answers` |
| C4 | **Incident en salle = perte du temps.** Le chronomètre est l'horloge murale serveur (`started_at + 30 min`). Une coupure ne met jamais le chrono en pause. La seule issue est un rattrapage, qui crée une nouvelle tentative avec de nouvelles questions. | `routers/exam_runtime.py:_deadline`, `routers/center_incidents.py:131-145` |
| C5 | **Comptes de démonstration à mot de passe connu.** `CodeRoute2026!` est documenté dans le README, QUICKSTART, DEMARRAGE_LOCAL et DEMO. Le README de production (étape 5) invite à lancer `seed_full` en production, ce qui créerait ces comptes. La variable citée (`ALLOW_SEED_IN_PROD`) n'est pas celle que le garde vérifie (`ALLOW_DEMO_SEED_NON_DEV`). | `README.md:52-54,114-120`, `seed_full.py:46-60` |

### Élevés

| # | Risque | Preuve |
|---|---|---|
| E1 | Fichiers d'environnement réels **suivis par git** : `.env.dev`, `frontend/.env.local`, `frontend/.env.production`. Leur contenu n'a pas été lu (règle de l'audit) : un humain doit vérifier qu'ils ne contiennent aucun secret, et les rotations éventuelles. | `git ls-files` |
| E2 | Jetons d'accès et de rafraîchissement stockés en `localStorage` : exposés à toute faille XSS. | `frontend/src/authClient.ts:52,60` |
| E3 | Pas de révocation de session : pas de `jti` ni de `token_version`. Un compte désactivé est bloqué (`is_active`), mais un jeton volé reste valide jusqu'à son expiration, et une déconnexion ne l'invalide pas. | `deps.py:16-24`, `security.py` |
| E4 | 2FA disponible mais **non imposée** aux rôles `admin` et `super_admin`. | `routers/auth.py:210-290`, `two_factor.py` |
| E5 | Tentatives orphelines : aucune tâche serveur ne finalise les examens expirés. La finalisation dépend d'un appel du navigateur (`timeout-submit`) ou d'une consultation de `/status`. | `routers/exam_runtime.py:160` ; aucun planificateur trouvé |
| E6 | La surveillance antifraude n'est **pas alimentée** : l'API `POST /exam-monitoring/events` existe, mais aucun code frontend n'émet d'événement (sortie de plein écran, perte de focus, etc.). | `routers/exam_monitoring.py:76`, aucun appel dans `frontend/src` |
| E7 | Paramètres réglementaires codés en dur (40 questions, seuil 35, 30 min, répartition, capacité 35, 3 sessions par semaine), sans version ni date d'effet : impossible de prouver quelle règle s'appliquait à un examen passé. | `exam_engine.py:27-40`, `session_rules.py:13-15`, `routers/exams.py:495` (`threshold=35`) |
| E8 | Fusion dans `main` = déploiement : `render.yaml` utilise `autoDeployTrigger: checksPass`. | `render.yaml:19,211,261` |
| E9 | Hébergement prévu à Francfort (`region: frankfurt`). La conformité avec le droit guinéen des données personnelles et l'éventuelle exigence d'hébergement national **sont à confirmer**. | `render.yaml:10,23` |

### Moyens

| # | Risque | Preuve |
|---|---|---|
| M1 | Réécriture de routes au démarrage : les gardes remplacent les routes historiques par manipulation de `router.routes`, ou en substituant une fonction de module (`exams._create_exam_attempt = …`). Le mécanisme refuse de démarrer en cas d'ambiguïté (fail-closed), mais le comportement réel est difficile à lire et à auditer. | `routers/__init__.py:60-200` |
| M2 | `create_all` est non bloquant en cas d'échec (dégradation silencieuse). `AUTO_CREATE_TABLES=True` par défaut. | `db/session.py:106-117`, `core/config.py:21` |
| M3 | Notifications : les exceptions sont capturées en bloc ; un échec d'envoi n'est que tracé dans Sentry, sans file de réessai. | `routers/exams.py:688-727` |
| M4 | URL de certificat codée en dur (`https://api.coderoute.gov.gn/...`) dans le flux de soumission, alors qu'un réglage `public_app_url` existe. | `routers/exams.py` (3 occurrences dans `app/`) |
| M5 | ~~Questions encore lisibles après expiration~~ — **voulu** : la reprise d'une tentative `expired` recharge les questions avant de la finaliser (`timeout-submit`), et aucune réponse n'est acceptée après l'échéance. Pas de correctif. | `routers/exam_media_guard.py:86`, `frontend/src/pages/exam.tsx:280-315` |
| M6 | Rattachement candidat ↔ compte par **égalité d'e-mail** en plus de `user_id` : un dossier créé par une auto-école avec l'e-mail d'un tiers devient accessible au compte qui porte cet e-mail. Exploitabilité **à vérifier**. | `routers/exams.py:338-342`, `routers/exam_runtime.py:37-41` |
| M7 | Médias de démonstration tronqués (3 webp de 7,5 Ko et 1 mp4 de 7,5 Ko, illisibles). | `frontend/public/media/exam/guinea/` |
| M8 | Audio en langues nationales annoncé, mais **aucun enregistrement** : les dossiers `frontend/public/audio/{ff,man,sus,kss,gkp,lom}` sont vides, et la synthèse vocale du navigateur ne couvre pas ces langues. | `question_i18n.py:18-37`, `frontend/public/audio/` |
| M9 | Aucun test unitaire frontend (pas de Vitest) ; la couverture UI repose sur 21 specs Playwright. | `frontend/package.json` |

### Faibles

- README obsolète : 111 endpoints, 5 migrations, 404 tests, Vite 6. Réel : 17 migrations, 1 302 fonctions de test, Vite 8.
- 144 documents dans `docs/`, dont une partie est historique ; aucune source de vérité désignée.
- Libellés de catégories incohérents entre le frontend (`Sécurité`, `Feux tricolores`) et le backend (`securite_passive`, …) : `frontend/src/pages/exam.tsx:182-193`.

## 3. Inventaire par domaine (points de l'audit)

### 3.1 Fonctionnalités réellement implémentées
Voir `MATRICE_FONCTIONNELLE.md` (73 fonctionnalités classées : 41 ✅, 12 🟡, 17 ❌, 3 ❔).

### 3.2 Écarts entre le README et le code

| Affirmation du README | Réalité |
|---|---|
| « Banque de 19 600 questions — 8 catégories, 8 langues » | 40 questions officielles + 160 d'entraînement, en français uniquement ; 0 traduction, 0 audio |
| « 111 endpoints », « 5 migrations », « 404+ tests » | 63 modules de routes, 17 migrations, 1 302 tests (1 312 cas exécutés en CI, couverture 84 %) |
| « Certificats numériques — QR code vérifiable publiquement » | Vrai (`#/verifier/<id>`, `GET /exams/{id}/certificate/verify`) |
| « Paiements Mobile Money — Orange, Wave, MTN, Moov » | Dispatcher et webhooks signés présents ; intégrations réelles **non vérifiées** (sandbox en démo) |
| « Anti-fraude — monitoring examen » | API présente mais non alimentée par le poste candidat (E6) ; détection statistique par centre présente (`center_anomalies.py`) |
| Déploiement : `ALLOW_SEED_IN_PROD=true seed_full` | Variable inexistante ; la commande échoue (heureusement), mais elle crée des comptes connus si on l'adapte |

### 3.3 Moteur d'examen et calcul du résultat
- **Sélection** : tirage par catégorie avec `random.Random(seed)`, où `seed` vaut `None` en production (`exam_engine.py:select_exam_questions`) : le tirage n'est pas rejouable, mais il est tracé (`ExamQuestionTrace` : ids, hash de la banque, hash de la sélection).
- **Notation** : `score_answers` compte bonnes, fausses et sans réponse ; admis si au moins 35/40, ou au prorata si le total diffère.
- **Soumission manuelle** : exige une réponse à chaque question (`exam_submit_completion_guard.py`).
- **Autosauvegarde serveur** : `POST /exams/{id}/answers`, avec un verrou de ligne et le refus des envois après l'échéance.
- **Finalisation automatique** : `timeout-submit` note la dernière copie serveur (tolérance de 2 s).
- **Idempotence** : une seconde soumission est rejouée sans effet et journalisée (`exam.replay_submission`).
- **Confidentialité** : questions servies sans `correct_answer` ; résultat candidat limité au score et aux fautes par thème (PR #254) ; correction détaillée réservée aux administrateurs.
- **Manques** : réponses multiples, pondération, questions éliminatoires, versionnement des règles, publication différée, pause sur incident.

### 3.4 Banque de questions, médias, traductions
- Modèle `Question` : `validation_status` (draft → submitted → approved/rejected), `version`, `validated_by`, `translations` (JSON).
- **Pas d'historique de versions** : une modification écrase le contenu, sans révision immuable. Une tentative ne référence que des `question_id` : si une question est éditée après l'examen, la correction affichée en recours ne reflète plus ce que le candidat a vu.
- Gouvernance média avancée (`media_policy`, `official_media_readiness`, revue média, contrôle HTTPS/alt) : implémentée et testée, mais **aucune question officielle n'a de média**.
- Traductions : le choix « texte en français, audio en langue nationale » est documenté (`question_i18n.py`), mais aucun audio n'existe.

### 3.5 Interfaces
| Interface | État |
|---|---|
| Candidat (`candidate.tsx`, `exam.tsx`, `results.tsx`) | Parcours complet ; chrono et progression visibles ; navigation séquentielle ; raccourcis clavier 1-4 ; reprise après rafraîchissement |
| Centre (`center.tsx`, `CenterEdgeOperationsPage.tsx`) | Contrôle d'entrée (QR/code), incidents, postes, passerelle edge |
| Auto-école (`driving-school.tsx`) | Inscription de candidats ; peu de routes dédiées (1 seul `require_roles("driving_school")`) : **partiel** |
| Administration / ministère (`admin.tsx`, `ministerial.tsx`, `NationalDashboard`) | Très riche : gouvernance, médias, finances, audit, régions |
| Familiarisation | Mode « examen blanc » et entraînement ; **pas de tutoriel guidé** avant l'épreuve officielle |

### 3.6 Authentification, autorisations, antifraude
- JWT HS256 (30 min) + refresh, bcrypt, limitation des tentatives de connexion, CSRF, 2FA TOTP optionnelle.
- Autorisations par rôle (`require_roles`, 5 rôles) et par périmètre de centre (`center_id`, `CENTER_SCOPE_MISMATCH`).
- Antifraude : contrôle d'identité obligatoire, fenêtres d'entrée et de démarrage, registre des postes, `DeviceSession`, verrou de tentative, trace hachée, audit HMAC chaîné, anomalies statistiques par centre, remboursements à quatre yeux.

### 3.7 Migrations, tests, CI/CD, déploiement
- 17 migrations Alembic linéaires, une seule tête (`0017`).
- 1 302 fonctions de test (pytest, SQLite) ; la suite complète est bloquante en CI depuis #255 ; couverture 84 %.
- 20 workflows GitHub Actions : CI, E2E fullstack, médias, supply chain edge, HA, PITR, SOC, gouvernance, go-live.
- Déploiement Render (Francfort), `preDeployCommand: ./scripts/predeploy.sh`, migrations exclues du démarrage en production.

### 3.8 Perte de réponses et défaillance réseau
| Scénario | Comportement actuel | Évaluation |
|---|---|---|
| Rafraîchissement / plantage du navigateur | Copie `sessionStorage` + copie serveur, reprise automatique | OK |
| Coupure réseau courte | File FIFO d'autosauvegarde, état « hors ligne », copie locale prioritaire | OK |
| Coupure WAN du centre | Passerelle edge (bail signé Ed25519, journal chaîné, chrono monotone) | Implémenté, **non éprouvé sur le terrain** |
| Coupure à l'échéance | La dernière copie serveur fait foi ; les réponses locales non synchronisées sont **perdues** | Risque résiduel |
| Panne de poste | Reprise sur un autre poste enregistré (`attempt_resumed`) ; le temps continue de courir | C4 |
| Candidat parti, navigateur fermé | La tentative reste `started` ou `expired` | E5 |
| Fermeture de l'onglet | `sessionStorage` perdu ; copie serveur intacte | OK |

### 3.9 Données de démonstration et secrets exposés
- Mot de passe commun `CodeRoute2026!` dans 5 documents et dans `seed_full.py` (C5).
- Clé de réponse officielle publique (C1).
- `.env.dev`, `frontend/.env.local` et `frontend/.env.production` suivis par git (E1, contenu non lu).
- Démo : `PASSWORD` codé en dur dans `scripts/demo_rehearsal.py` (acceptable : comptes jetables).
- La validation des secrets de production existe et refuse les secrets factices ou faibles (`core/config.py:118-170`).

### 3.10 Exigences réglementaires guinéennes à confirmer
Voir `ANALYSE_ECARTS_FRANCE_GUINEE.md` §4 : la liste des 18 décisions que la DNTT doit trancher. **Aucune règle guinéenne n'a été supposée dans ce dossier.**

## 4. Limites de cet audit
- Tests non relancés pour cet audit : les résultats cités sont ceux de la CI `main` @ `3b9318d` (6/6 workflows verts).
- Intégrations Mobile Money, SMS et WhatsApp non testées contre les vrais fournisseurs.
- Passerelle edge : revue du code et des tests seulement, sans essai sur du matériel réel.
- Contenu des fichiers `.env*` suivis non inspecté, volontairement.
