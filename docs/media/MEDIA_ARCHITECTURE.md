# CodeRoute Guinée — Architecture média premium

## Statut

Phase 2 — architecture BDD additive et rétrocompatible.

Cette phase ne change pas encore la sélection d'un média dans l'examen. Les champs legacy `Question.media_type`, `Question.media_url` et `Question.media_alt` restent actifs jusqu'à la migration de contenu et au basculement contrôlé des lectures.

## Objectifs

La couche média doit permettre de répondre de façon vérifiable à huit questions :

1. Quel fichier exact a été affiché ?
2. Où est-il stocké et comment est-il livré ?
3. Quelle est sa qualité technique ?
4. Quelle est sa provenance ?
5. Quels droits permettent son utilisation ?
6. Qui l'a validé pédagogiquement ?
7. Quel est son statut réglementaire pour la Guinée ?
8. À quelle question et dans quel rôle est-il rattaché ?

## Modèle `MediaAsset`

Un `MediaAsset` représente un fichier ou une ressource média identifiée indépendamment des questions.

### Identité

- `id` : clé primaire interne UUID string ;
- `uuid` : identifiant stable externe, unique ;
- `media_type` : `image`, `video`, `audio` ;
- `usage_type` : `exam`, `course`, `explanation`, `thumbnail`.

### Stockage/livraison

- `storage_provider` ;
- `storage_key` ;
- `public_url` ;
- `secure_url`.

Aucun credential de stockage n'est persisté dans cette table.

### Qualité technique

- `mime_type` ;
- `width` ;
- `height` ;
- `duration_seconds` ;
- `file_size_bytes` ;
- `checksum_sha256`.

Le checksum sert à identifier la version binaire réellement validée et à détecter les doublons ou remplacements.

### Composition vidéo

- `poster_media_id` ;
- `fallback_media_id`.

Ces deux champs sont des auto-références vers `media_assets` et sont nullable pendant la phase de construction. Le futur quality gate rendra poster + fallback obligatoires pour une vidéo d'examen avant publication.

### Classification

- `theme` ;
- `subtheme` ;
- `country_code` ;
- `regulatory_scope`.

`country_code` vaut `GN` par défaut mais ce défaut n'est pas une homologation réglementaire.

### Provenance et droits

- `source_type` : `original`, `licensed`, `partner`, `public_domain`, `internal`, `generated`, `legacy` ;
- `source_reference` ;
- `license_type` ;
- `license_reference` ;
- `license_expiration_date` ;
- `copyright_owner`.

Le statut `legacy` permet de migrer une référence existante sans la faire passer artificiellement pour un contenu original ou sous licence vérifiée.

### Validation

- `quality_status` : `draft`, `review_required`, `validated`, `rejected` ;
- `regulatory_status` : `not_reviewed`, `under_review`, `validated`, `rejected` ;
- `regulatory_authority_reference` ;
- `validated_by` ;
- `validated_at`.

Les défauts sont volontairement fail-closed : `draft` et `not_reviewed`. Aucune création d'asset ne produit automatiquement un média officiel.

### Cycle de vie

- `created_by` ;
- `created_at` ;
- `updated_at` ;
- `archived_at`.

L'archivage est préféré à la suppression physique pour conserver l'historique de preuve.

## Modèle `QuestionMedia`

Une question peut être liée à plusieurs médias et un même média peut être réutilisé lorsque cela est pédagogiquement justifié.

Champs :

- `question_id` ;
- `media_id` ;
- `role` ;
- `display_order`.

Rôles :

- `primary` : média principal présenté dans la question ;
- `poster` : poster explicite ;
- `fallback` : média de secours ;
- `explanation` : média utilisé dans la correction.

Une contrainte unique `(question_id, media_id, role)` évite les doublons accidentels.

## Compatibilité legacy

Pendant la migration :

1. si une question possède un `QuestionMedia(primary)` éligible, le futur resolver pourra le servir ;
2. sinon les champs `Question.media_*` continueront d'être utilisés ;
3. les SVG `sign/scene` restent disponibles comme compatibilité mais ne sont jamais assimilés automatiquement à un média premium validé ;
4. aucune colonne legacy n'est supprimée en Phase 2.

## Invalidation future

La Phase 3/4 devra introduire une règle forte :

- changement de binaire / checksum → `quality_status=review_required` ;
- si le média avait une validation réglementaire → `regulatory_status=under_review` ;
- la publication d'une question pour examen officiel est refusée tant que le média principal requis n'est pas conforme au quality gate.

Cette logique n'est volontairement pas activée en Phase 2 afin de ne pas modifier le comportement métier avant que les API et workflows administratifs correspondants existent.

## Migration Alembic

`0015` crée uniquement :

- `media_assets` ;
- `question_media` ;
- contraintes de domaine ;
- clés étrangères ;
- index de recherche/filtrage.

`down_revision = 0014`.

La migration doit fonctionner sur PostgreSQL/Neon et sur SQLite pour les tests de migration depuis une base vide.

## Phases suivantes

### Phase 3

API média + validation serveur + abstraction storage.

### Phase 4

Back-office `/admin/media-library` + workflow de validation.

### Phase 5

Resolver media + `ExamMediaPlayer` basé prioritairement sur `MediaAsset`, avec fallback legacy.

### Phase 6

Médias de correction pédagogiques.

### Phase 7

Backfill progressif des références existantes et remplacement des mappings incorrects.

Aucun remplacement massif de contenu ne doit précéder cette architecture de traçabilité.
