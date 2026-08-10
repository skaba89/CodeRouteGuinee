# CodeRoute Guinée — Audit média Phase 1

Date: 2026-08-10
Périmètre: images, vidéos et illustrations utilisées dans les questions d’entraînement, examens simulés et examens officiels.

## 1. Conclusion exécutive

Le problème principal n’est pas le lecteur média. CodeRoute dispose déjà d’un lecteur image/vidéo correct et d’un flux Cloudinary signé, mais la banque actuelle est majoritairement alimentée par des illustrations SVG synthétiques internes (`sign` / `scene`) choisies automatiquement à partir du texte des questions. Cette stratégie produit des visuels génériques, répétitifs et parfois sans rapport exact avec la situation évaluée.

**Score média actuel estimé : 4,5 / 10.**

Points forts :
- support réel `image` / `video` déjà présent ;
- HTTPS et protections SSRF sur les URLs finales ;
- upload Cloudinary signé ;
- politique minimale 1280x720 ;
- player vidéo avec poster Cloudinary dérivé, preload metadata, retry et plein écran ;
- workflow DNTT de validation des questions déjà présent.

Points bloquants :
- pas de modèle `MediaAsset` indépendant ;
- pas de checksum SHA-256 par média ;
- pas de source/licence/copyright par média ;
- pas de statut QA média indépendant de la validation de la question ;
- pas de statut réglementaire média ;
- pas de poster/fallback persistés en base ;
- pas de média de correction distinct ;
- pas de dimensions/durée/taille persistées ;
- pas de médiathèque administrateur ;
- pas de vraie couverture photo/vidéo réaliste ;
- mécanisme de mapping automatique pouvant associer une scène incorrecte ;
- les SVG actuels sont des dessins pédagogiques, pas des scènes réalistes de niveau examen moderne.

## 2. Architecture actuelle

### Backend

`Question` stocke directement :
- `media_type` ;
- `media_url` ;
- `media_alt`.

Il n’existe pas encore de table média normalisée permettant plusieurs médias par question, la provenance, la licence, le poster, le fallback, la correction, le checksum ou l’historique de validation média.

Les écritures externes acceptent `image` / `video`. La lecture accepte en plus les types internes historiques `sign` / `scene`.

### Upload

Le backend fournit une signature Cloudinary afin que les fichiers soient uploadés directement du navigateur vers Cloudinary. Les secrets restent côté serveur.

La politique actuelle prévoit :
- image : max 10 MiB, JPEG/PNG/WebP/AVIF, minimum recommandé 1280x720 ;
- vidéo : max 80 MiB, max 30 s, MP4/WebM/QuickTime, minimum recommandé 1280x720, poster requis, delivery adaptatif annoncé.

### Frontend

`ExamMediaPremium` gère les vraies URLs `image` et `video`.

Pour les types internes `sign` et `scene`, le frontend retombe sur le renderer legacy basé sur de gros composants SVG dessinés à la main.

Deux bibliothèques importantes sont actuellement présentes :
- `frontend/src/pages/illustrations.tsx` ;
- `frontend/src/pages/illustrations_signs.tsx`.

Ces fichiers produisent des scènes 800x420 en SVG : routes, voitures, panneaux, végétation, bâtiments, tableau de bord, etc. Elles sont adaptées comme schémas pédagogiques mais insuffisantes pour simuler une situation photographique/vidéo réelle de niveau premium.

## 3. Cause racine des mauvais visuels

### 3.1 Mapping heuristique du seed

`backend/app/seed_full.py::_get_media_for_question()` choisit un média à partir de mots-clés présents dans le texte.

Exemples de règles problématiques :
- `passage à niveau` peut tomber sur `traffic_light_red` ;
- une `ligne continue` est représentée par `no_overtaking` ;
- les questions de sécurité passive sans correspondance précise tombent sur `situation_safe_distance` ;
- les urgences tombent par défaut sur `situation_emergency_vehicle` ;
- la signalisation sans correspondance utilise un panneau choisi par hash ;
- les questions vitesse utilisent un panneau choisi parmi plusieurs vitesses par hash.

Cette approche garantit qu’un visuel existe, mais pas qu’il soit pédagogiquement exact.

### 3.2 Démonstration frontend

La banque de démonstration contient plusieurs associations manifestement incohérentes :

| Question | Sujet | Média actuel | Statut audit |
| --- | --- | --- | --- |
| q09 | passage à niveau | `intersection_priority_right` | REJECTED |
| q13 | pluie battante | `speed_30` | REJECTED |
| q14 | distance d’arrêt à 90 km/h | `speed_110` | REJECTED |
| q17 | tourner à gauche | `no_overtaking` | REVIEW_REQUIRED |
| q18 | ligne blanche continue | `danger_generic` | REJECTED |
| q19 | feu orange clignotant | `stop` | REJECTED |
| q30 | verglas | `situation_emergency_vehicle` | REJECTED |
| q36 | écoconduite / pollution | `first_aid` | REJECTED |
| q37 | feu vert piéton | `give_way` | REJECTED |
| q38 | somnolence | `situation_safe_distance` | REJECTED |
| q39 | piéton + virage à gauche | `intersection_priority_right` | REJECTED |

Ce tableau n’est pas exhaustif.

## 4. Risques

### P0 — qualité pédagogique

Une image sans rapport exact avec la question peut enseigner le mauvais signal visuel au candidat et réduit fortement la crédibilité de la plateforme.

### P0 — homologation

La validation actuelle porte principalement sur la question. Un changement de `media_url` n’invalide pas automatiquement une validation réglementaire média dédiée, puisqu’elle n’existe pas encore.

### P1 — traçabilité

Une URL média seule ne permet pas de prouver :
- quel fichier exact a été validé ;
- sa licence ;
- son propriétaire ;
- sa résolution ;
- sa durée ;
- son hash ;
- qui l’a validé ;
- quelle version était affichée le jour d’un examen.

### P1 — répétition / artificialité

Les mêmes scènes SVG sont utilisées pour de nombreuses questions différentes. La banque donne donc un aspect répétitif et artificiel, très différent d’une plateforme premium fondée sur des situations réelles.

### P1 — conformité géographique

Les commentaires de code parlent de panneaux français normalisés et d’un rendu inspiré d’applications françaises. Cela ne constitue pas une validation réglementaire guinéenne. Tout média destiné à une épreuve nationale doit disposer de sa propre validation de périmètre.

### P2 — accessibilité

`media_alt` existe, mais il faut éviter qu’un alt d’une question d’examen révèle indirectement la réponse. Les médias pédagogiques doivent en revanche pouvoir porter description, sous-titres et transcription.

## 5. Classification cible Phase 1

Chaque média devra pouvoir être classé :
- `VALIDATED`
- `REVIEW_REQUIRED`
- `LOW_QUALITY`
- `BROKEN`
- `MISSING`
- `COPYRIGHT_UNKNOWN`
- `REGULATORY_REVIEW_REQUIRED`
- `REJECTED`

Pour la banque legacy actuelle :
- `sign` / `scene` : au minimum `REVIEW_REQUIRED` pour examen premium ;
- mapping sémantiquement incohérent : `REJECTED` ;
- URL image/vidéo sans provenance/licence : `COPYRIGHT_UNKNOWN` ;
- média réel non homologué : `REGULATORY_REVIEW_REQUIRED`.

## 6. Standard minimum recommandé

### Image examen
- 1280x720 minimum ;
- 1920x1080 préféré ;
- WebP/JPEG ;
- 16:9 ;
- pas de watermark ;
- scène non ambiguë ;
- détail déterminant clairement visible sur smartphone.

### Vidéo examen
- 1280x720 minimum ;
- 1920x1080 préféré ;
- MP4/H.264 comme format de référence ;
- 6 à 20 secondes recommandé ;
- poster obligatoire ;
- fallback image obligatoire ;
- usage vidéo seulement si le mouvement est nécessaire à la compréhension.

## 7. Architecture cible à préparer en Phase 2

Créer une entité indépendante `MediaAsset` et une relation `QuestionMedia`.

`MediaAsset` devra porter au minimum :
- type et usage ;
- storage provider/key ;
- URL de livraison ;
- MIME ;
- dimensions ;
- durée ;
- taille ;
- SHA-256 ;
- poster/fallback ;
- thème/sous-thème ;
- pays/périmètre réglementaire ;
- source/provenance ;
- licence/copyright ;
- statut qualité ;
- statut réglementaire ;
- validateurs et horodatages.

`QuestionMedia` permettra les rôles :
- PRIMARY ;
- POSTER ;
- FALLBACK ;
- EXPLANATION.

## 8. Migration sans régression

Ordre obligatoire :

1. ajouter le nouveau modèle sans supprimer `Question.media_*` ;
2. backfiller les anciennes références comme assets `LEGACY` / `REVIEW_REQUIRED` ;
3. lecture : nouveau média validé → legacy → fallback contrôlé ;
4. introduire la médiathèque et la validation ;
5. migrer progressivement les questions prioritaires ;
6. mesurer 100 % de couverture avant toute dépréciation ;
7. supprimer les colonnes legacy seulement dans une phase ultérieure dédiée.

## 9. Priorité de remplacement

### Lot A — critique
- intersections/priorités ;
- piétons/cyclistes ;
- dépassement ;
- insertion/changement de voie ;
- pluie/brouillard/nuit ;
- distances de sécurité/freinage ;
- passage à niveau ;
- véhicules prioritaires.

Ces sujets doivent être photographiques ou vidéo lorsque le contexte spatial/dynamique est déterminant.

### Lot B
- panneaux isolés ;
- marquages ;
- feux ;
- équipements véhicule.

Une photo HD ou un rendu vectoriel officiellement validé peut suffire.

### Lot C
- alcool ;
- fatigue ;
- premiers secours ;
- écoconduite.

Les médias doivent être contextualisés et non réutilisés comme simple décoration.

## 10. Fichiers identifiés pour les phases suivantes

Backend :
- `backend/app/models_question.py`
- `backend/app/schemas.py`
- `backend/app/routers/questions.py`
- `backend/app/media_policy.py`
- `backend/app/cloudinary_service.py`
- `backend/app/seed_full.py`
- migrations Alembic

Frontend :
- `frontend/src/components/ExamMediaPremium.tsx`
- `frontend/src/pages/shared-exam-components.tsx`
- `frontend/src/pages/shared-exam-components-legacy.tsx`
- `frontend/src/pages/illustrations.tsx`
- `frontend/src/pages/illustrations_signs.tsx`
- `frontend/src/pages/exam.tsx`
- `frontend/src/pages/examQuestions.ts`
- administration des questions / futur `/admin/media-library`

Tests :
- `backend/tests/test_media_policy.py`
- nouveaux tests `MediaAsset`, publication et provenance ;
- nouveaux E2E Playwright image/vidéo/fallback/admin.

## 11. Décision Phase 1

**GO pour Phase 2**, avec une condition : ne pas chercher à « améliorer » les SVG legacy comme solution finale. Ils doivent devenir une solution de compatibilité / démonstration, puis être remplacés progressivement par des assets premium validés.

La priorité architecture est de découpler la validation de la question de la validation de son média. Le prochain chantier doit donc être la couche `MediaAsset` + `QuestionMedia` + migrations rétrocompatibles, avant tout remplacement massif de contenu.
