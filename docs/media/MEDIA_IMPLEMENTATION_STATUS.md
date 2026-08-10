# CodeRoute Guinée — État d'industrialisation des médias

## Règle de lecture

Ce document distingue strictement :

- la **capacité technique** de la plateforme ;
- la **qualité réelle des contenus** actuellement utilisés par l'examen ;
- la **validation humaine/réglementaire** des futurs médias.

Une architecture premium ne signifie pas que les images/vidéos historiques sont déjà devenues premium.

## Phase 1 — Audit : TERMINÉE

Le problème principal identifié est la sélection sémantique des contenus historiques : le seed associe des identifiants `sign/scene` via des heuristiques de texte et de catégorie. Plusieurs scènes sont techniquement rendables mais pédagogiquement incohérentes avec la question.

Score initial de la chaîne média : **4,5/10**.

Livrables :
- audit média ;
- script d'inventaire ;
- tests de l'auditeur ;
- plan de correction.

## Phase 2 — Architecture BDD : TERMINÉE

`MediaAsset` et `QuestionMedia` sont additifs et conservent les champs legacy.

Sont disponibles :
- identité fichier ;
- stockage ;
- MIME/dimensions/durée/taille ;
- SHA-256 ;
- poster/fallback ;
- thème ;
- provenance ;
- licence/copyright ;
- qualité ;
- réglementation ;
- validateurs ;
- archivage ;
- rôles primary/poster/fallback/explanation.

## Phase 3 — API + storage : TERMINÉE

Sont disponibles :
- API admin de médiathèque ;
- recherche/filtrage ;
- création/update/archive ;
- association question ↔ média ;
- détection de doublon par SHA-256 ;
- invalidation d'une validation après modification sensible ;
- Cloudinary signé ;
- S3 / R2 / MinIO via URL pré-signée ;
- séparation entre URL d'upload temporaire et URL de lecture durable ;
- politique anti-SSRF et MIME.

## Phase 4 — Quality gate + back-office : TERMINÉE

Sont disponibles :
- score qualité ;
- HD minimum 1280x720 ;
- vidéo examen 6–20 secondes ;
- poster/fallback requis pour vidéo d'examen ;
- provenance/droits ;
- workflow qualité ;
- workflow réglementaire ;
- règle des quatre yeux ;
- blocage d'approbation d'une question normalisée si le média n'est pas publiable ;
- compatibilité temporaire des questions legacy ;
- back-office `#/admin/media-library` ;
- upload direct provider ;
- SHA-256 calculé côté navigateur ;
- tests backend + E2E médiathèque intégrés au gate national.

Une référence d'autorité enregistrée par le logiciel n'est pas en elle-même une preuve d'homologation. La décision institutionnelle reste humaine.

## Phase 5 — Runtime candidat : EN COURS

Le resolver backend est développé :

- média normalisé pleinement validé → priorité ;
- média normalisé non publiable → jamais exposé ;
- vidéo normalisée → poster + fallback ;
- fallback legacy temporaire pendant migration ;
- absence totale → état `none` contrôlé ;
- résolution batch ;
- aucune donnée de licence/audit/autorité envoyée au candidat.

Reste à terminer avant de déclarer la Phase 5 complète :

1. endpoint candidat-safe du resolver ;
2. intégration dans le player d'examen ;
3. préchargement N+1 contrôlé ;
4. fallback réseau/offline ;
5. E2E image premium ;
6. E2E vidéo premium ;
7. E2E erreur vidéo → fallback image ;
8. viewport mobile/desktop ;
9. mesure LCP/CLS/payload initial.

## Phases 6–10 — NON TERMINÉES

### Phase 6
Médias de correction pédagogiques.

### Phase 7
Backfill et remplacement progressif des médias historiques.

C'est **la phase qui corrigera réellement l'ensemble des mauvaises images/vidéos actuellement visibles**.

Elle exige de vrais contenus :
- captations originales ;
- partenaires/auto-écoles ;
- médias sous licence ;
- éventuellement contenu généré/3D uniquement après revue et sans auto-homologation.

### Phase 8
Recette complète/non-régression.

### Phase 9
Performance et réseau mobile.

### Phase 10
Rapport final et PR de clôture.

## Bloquants externes honnêtes

Le code ne peut pas créer à lui seul :

- les droits d'utilisation d'une photographie tierce ;
- une captation réelle de circulation ;
- une validation DNTT ;
- une décision juridique ;
- une preuve de licence qui n'existe pas.

Ces éléments doivent être fournis/produits puis attachés à la médiathèque. Aucun média ne sera marqué officiel artificiellement.
