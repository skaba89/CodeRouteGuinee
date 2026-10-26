# EX-01 — Plan de changement : copie immuable d’une épreuve

Base revue : `main` @ `71f6628233f4bca1756017830e2ba8f4d13bb047`.
Statut : proposition à valider avant implémentation. Ce document ne contient
ni migration exécutée, ni modification du moteur d’examen.

## Problème vérifié et résultat attendu

Une tentative conserve les identifiants des questions, mais pas leur contenu.
La soumission (`routers/exams.py:637`), le timeout (`routers/exam_runtime.py:193`)
et la synchronisation Edge (`routers/center_edge_offline.py:502`) reconstruisent
la correction depuis les lignes Question actuelles. L’import officiel réécrit
ces lignes. L’affichage candidat et la consultation des traces les relisent aussi.

Invariant cible : après le démarrage, texte, ordre, options et correction de
la tentative sont ceux capturés à sa création. Modifier ou désactiver une
question source n’altère ni la copie ni le score de cette tentative. Une
nouvelle tentative voit le contenu approuvé applicable à son démarrage.

Les règles actuelles (40 questions, seuil 35, 30 minutes et répartition courante)
restent inchangées et provisoires. Leur valeur effective est capturée pour la
traçabilité ; cela ne vaut pas homologation DNTT. Aucune réponse multiple,
pause, nouvelle pondération ou nouvelle règle de publication n’est introduite.

## Choix proposé

Créer une copie complète **par tentative**, plutôt que refondre immédiatement
le workflow global de versionnement de la banque. Les futures révisions de
questions pourront compléter ce mécanisme ; elles ne sont pas nécessaires pour
empêcher une édition de banque de modifier la correction d’une tentative.

Nouvelle table `exam_attempt_snapshots` :

- `id`, `attempt_id` unique (FK), `trace_id` unique (FK), `schema_version`,
  `captured_at`, `payload` JSON et `payload_hash` ;
- payload interne : ordre et identifiants, texte, catégorie, options,
  correction/explication réservées au serveur, contenus linguistiques utilisés,
  références et métadonnées de diffusion des médias, paramètres effectifs ;
- empreinte canonique SHA-256 couvrant le contenu complet, associée à un
  événement du journal HMAC existant. Le hash n’est pas présenté comme une
  signature institutionnelle et ne protège pas seul contre un administrateur DB ;
- refus des UPDATE/DELETE par le rôle applicatif : garde ORM et protection
  PostgreSQL à vérifier sous le rôle réel. Le rôle de migration reste distinct.
  Aucun endpoint de modification de snapshot.

Tentative, trace et snapshot sont créés dans la même transaction : aucune
création partielle ne doit être visible. Les questions sélectionnées sont
revalidées pendant la capture avec un ordre de verrouillage déterministe.
Un test PostgreSQL concurrent valide qu’une édition ne produit pas une copie
mélangeant deux versions. Les snapshots sont chargés en une requête par tentative.

Un lecteur serveur partagé vérifie version, empreinte, ordre, doublons et nombre
de questions. Pour une nouvelle tentative, snapshot absent/incomplet/altéré =
refus explicite et audit ; **jamais de repli silencieux vers Question actuelle**.
La construction des réponses API est une projection explicite, séparée du
payload interne : aucune sérialisation brute du snapshot.

## Fichiers prévus

| Fichier | Modification proposée |
|---|---|
| `backend/app/models_exam_snapshot.py` (nouveau) | Modèle interne et garde d’immutabilité |
| `backend/app/models.py` | Enregistrement du modèle |
| `backend/alembic/versions/0018_exam_attempt_snapshots.py` (nouveau, numéro à revalider) | Migration additive depuis 0017, contraintes/index et protection DB |
| `backend/app/exam_snapshot.py` (nouveau) | Capture canonique, validation, lecteurs et projections |
| `backend/app/official_exam_attempt_service.py` | Capture atomique dans le chemin réellement monté |
| `backend/app/routers/exams.py` | Notation, résultat détaillé/summary et compatibilité des chemins historiques |
| `backend/app/routers/exam_runtime.py` | Reprise et timeout depuis la copie figée |
| `backend/app/routers/exam_media_guard.py` | Texte/options depuis la copie, diffusion média contrôlée |
| `backend/app/routers/exam_question_traces.py` | Présentation historique sans relire le contenu courant comme s’il était original |
| `backend/app/routers/center_edge_offline.py` | Bail et notation centrale depuis la même copie |
| `backend/app/routers/center_edge_station_guard.py` | Vérifier la délégation et conserver les signatures/liaisons poste |
| `backend/tests/conftest.py` et fabriques de traces existantes | Produire des copies valides dans les tests, sans contourner les gardes |
| Nouveaux tests snapshot / PostgreSQL et tests runtime/Edge existants | Matrice ci-dessous et non-régression |

Aucun changement de route, de rôle ni de permission prévu. L’agrégateur
`routers/__init__.py` doit être contrôlé : le constructeur historique est
remplacé par `create_media_safe_exam_attempt`. Modifier seulement une fonction
historique non montée ne corrigerait pas le chemin réellement exécuté.

## Médias et révocation

Figer une URL ne fige pas les octets hébergés. Conserver identifiant de version,
clé de stockage et checksum lorsqu’ils existent ; ne pas persister un ticket
éphémère comme seule référence. Si le stockage n’est pas versionné, cette
limite doit être visible et la conformité de la copie multimédia reste ouverte.
Le lot garantit d’abord l’immuabilité du texte, des options et de la correction.

Ne jamais remplacer silencieusement un média de la copie par le média courant
d’une question. Une révocation réglementaire ou une indisponibilité doit garder
les contrôles de sécurité existants et remonter un incident explicite. La
procédure métier de reprise/aménagement reste à valider avec DNTT ; le correctif
n’ajoute ni temps ni nouvelle question à la tentative.

## Tentatives historiques et compatibilité

Une copie d’origine manquante ne peut pas être reconstruite fidèlement en
copiant les questions actuelles. **Aucun backfill automatique présenté comme
historique, aucun recalcul de score, aucune réinitialisation des tentatives.**

Avant promotion : inventaire en lecture seule des traces sans snapshot et des
tentatives récupérables, y compris les baux Edge et synchronisations différées.
Ne pas promouvoir le basculement strict tant qu’une tentative commencée sous
l’ancien code ou un bail encore réconciliable demeure, sans procédure approuvée.
L’exploitant coordonne une fenêtre entre sessions ; aucune fermeture, expiration,
annulation ou finalisation forcée n’est effectuée par la migration.

Pour les tentatives soumises historiques : conserver score, passed, dates et
vérification de certificat existants. Si la copie d’origine est absente, les
écrans de recours ne doivent pas présenter la correction courante comme une
preuve historique : signaler explicitement l’indisponibilité de cette preuve.
Le comportement détaillé de ces écrans et les limites de compatibilité doivent
être acceptés avant implémentation. Les autorisations restent inchangées.

## Plan de tests obligatoire

| Scénario | Preuve attendue |
|---|---|
| Édition de texte/options/correction après démarrage | Ancienne tentative inchangée, nouvelle tentative actualisée si approuvée |
| Import officiel pendant une épreuve | Même copie et même score, aucune réécriture du snapshot |
| Soumission manuelle vs timeout | Même clé figée et même résultat pour les mêmes réponses |
| Reprise après refresh et remplacement de poste | Même ordre/options et même copie serveur |
| Bail Edge, édition puis synchronisation | Notation centrale conforme au contenu délivré avant coupure |
| Candidat et centre, succès et erreurs | Aucune correction/explication dans JSON, traces, exports, notifications ou logs |
| Snapshot absent, malformé, altéré ou incomplet | Refus explicite pour nouvelle tentative, pas de fallback à la banque vivante |
| UPDATE/DELETE ORM et SQL sous rôle applicatif | Immutabilité vérifiée sur PostgreSQL |
| Édition concurrente et création concurrente | Une seule trace/copie cohérente, absence de double finalisation |
| Legacy soumis / tentative en cours / bail différé | Aucune mutation historique ; prérequis de promotion détecté |
| Migration base vide et upgrade depuis 0017 avec données | Schéma cohérent, données inchangées, une seule tête Alembic |

Les migrations initiales utilisent les modèles courants : le test depuis base
vide peut masquer une omission. Construire aussi une base représentative de
0017 indépendante du nouveau metadata, puis appliquer l’upgrade. Ne pas modifier
les migrations historiques pour rendre les tests verts.

Exécuter les suites complètes backend, PostgreSQL réel et E2E navigateur, avec
fournisseurs/notifications factices. Conserver les tests de confidentialité,
station, échéance, idempotence, audit HMAC et médias. Les fixtures ne doivent
jamais rétablir un accès non authentifié ni accepter une copie vide.

## Promotion, risques et retour arrière

Ordre : migration additive en recette jetable → tests de lecture et écriture →
revue sécurité/domaine → inventaire legacy autorisé → validation explicite →
promotion manuelle. Aucun script de ce plan n’agit sur production.

Risques : stockage de corrections sensibles supplémentaires, dérive de copies
médias, volume et verrouillage, rupture des fabriques de tests historiques,
baux Edge survivant au changement de version, détail de recours indisponible
pour les anciennes tentatives. Chaque risque a un critère de test ou de
promotion ci-dessus.

Conserver la nouvelle table en cas de retour arrière ; ne pas lancer de downgrade
supprimant les preuves. Une ancienne version relirait la banque vivante et ne
sait pas respecter les nouvelles copies : pas de rollback applicatif automatique
sur des examens déjà commencés avec snapshots. Bloquer les nouveaux départs et
appliquer une procédure de reprise convenue plutôt que perdre la copie ou noter
avec une autre correction. Aucun résultat historique recalculé.

## Validation demandée

Le `CLAUDE.md`, section Workflow, impose pour les changements examen/migration :
« plan écrit (fichiers, impacts, risques, tests, rollback) → attendre un “OK” →
implémentation ». Ce plan concrétise le prochain changement majeur ; les PR
paiements et seed déjà intégrées ne valent pas validation de cette nouvelle
migration et de la compatibilité historique. Un accord sur ce plan autorisera
l’implémentation sur une branche dédiée, sans autoriser de déploiement ni de fusion.
