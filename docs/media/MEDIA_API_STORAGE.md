# CodeRoute Guinée — Phase 3 API média et stockage

## Objectif

La Phase 3 introduit une API de médiathèque indépendante des champs historiques `Question.media_type`, `Question.media_url` et `Question.media_alt`.

Le comportement actuel de l'examen n'est pas encore basculé vers `MediaAsset` : cette séparation est volontaire afin que l'architecture, la sécurité et les workflows administratifs puissent être validés avant toute migration du rendu candidat.

## Endpoints

Sous `/api/v1/media-library` :

- `GET /assets` : recherche/filtrage/pagination de la médiathèque ;
- `GET /assets/{media_id}` : détail d'un asset ;
- `POST /assets` : enregistrement d'un nouvel asset ;
- `PATCH /assets/{media_id}` : mise à jour des métadonnées ;
- `POST /assets/{media_id}/archive` : archivage logique ;
- `POST /upload-target` : cible d'upload courte durée selon le provider ;
- `GET /questions/{question_id}` : associations média d'une question ;
- `POST /questions/{question_id}/links` : associer un asset ;
- `DELETE /questions/{question_id}/links/{link_id}` : retirer une association.

Ces endpoints sont réservés aux rôles `admin` / `super_admin`.

## Fail-closed

Un asset créé par l'API démarre toujours avec :

- `quality_status = draft` ;
- `regulatory_status = not_reviewed`.

L'appelant ne peut pas déclarer un média `validated` au moment de sa création.

Toute modification d'une donnée qui fait partie de l'identité technique, des droits ou du périmètre réglementaire d'un média invalide une validation précédente :

- qualité validée/refusée → `review_required` ;
- réglementation validée/refusée → `under_review` ;
- `validated_by` / `validated_at` sont effacés.

Cette règle protège notamment les remplacements de fichier par changement de `checksum_sha256` ou d'URL.

## Validation serveur

Avant persistance, le backend vérifie notamment :

- URL HTTPS publique avec la politique anti-SSRF existante ;
- cohérence du type Cloudinary ;
- MIME autorisé ;
- taille maximale ;
- durée maximale ;
- SHA-256 sur 64 hex ;
- `storage_key` sans traversal ;
- références poster/fallback vers une image existante et non archivée.

La validation technique ne vaut jamais validation pédagogique ou réglementaire.

## Détection de doublon

Lorsque `checksum_sha256` est présent, l'API refuse un second asset actif portant le même checksum et retourne `409` avec l'identifiant du média déjà enregistré.

Cela évite la duplication involontaire d'un même fichier tout en laissant la possibilité d'archiver un asset historique.

## Cloudinary

Le flux existant est conservé :

1. le frontend demande une cible d'upload ;
2. le backend génère une signature courte durée ;
3. le navigateur envoie directement le fichier à Cloudinary ;
4. le secret API Cloudinary n'est jamais envoyé au navigateur ;
5. les métadonnées du fichier final sont ensuite enregistrées dans `MediaAsset`.

Variables existantes :

- `CLOUDINARY_CLOUD_NAME` ;
- `CLOUDINARY_API_KEY` ;
- `CLOUDINARY_API_SECRET` ;
- `CLOUDINARY_UPLOAD_FOLDER`.

Les fichiers audio sont des `MediaAsset(media_type=audio)` mais Cloudinary les transporte avec son `resource_type=video`, conformément au fonctionnement du fournisseur.

## S3 / Cloudflare R2 / MinIO

L'abstraction `MediaStorageProvider` accepte :

- `cloudinary` ;
- `s3` / `aws_s3` / `aws` ;
- `r2` / `cloudflare_r2` ;
- `minio`.

Variables :

- `MEDIA_STORAGE_PROVIDER` ;
- `MEDIA_S3_BUCKET` ;
- `MEDIA_S3_PREFIX` ;
- `MEDIA_S3_ENDPOINT_URL` ;
- `MEDIA_S3_REGION` ;
- `MEDIA_S3_ACCESS_KEY_ID` ;
- `MEDIA_S3_SECRET_ACCESS_KEY` ;
- `MEDIA_S3_SESSION_TOKEN`.

Pour S3-compatible, l'API génère une URL `PUT` signée de 15 minutes. Les credentials longue durée restent côté backend et ne sont jamais présents dans la réponse API.

`MEDIA_S3_ENDPOINT_URL` permet de cibler notamment R2 ou MinIO.

## Politique technique actuelle

### Images

- max 10 MiB ;
- JPEG, PNG, WebP, AVIF ;
- 1280x720 recommandé minimum.

### Vidéos

- max 80 MiB ;
- max 30 secondes au niveau de l'upload technique ;
- MP4, WebM, QuickTime ;
- poster requis par la politique ;
- 1280x720 recommandé minimum.

Le futur quality gate Phase 4 appliquera une durée recommandée plus stricte pour les médias d'examen (6–20 s) et imposera poster + fallback avant publication.

### Audio

- max 15 MiB ;
- max 10 minutes ;
- MPEG/MP4/OGG/WAV/WebM audio.

## Association question ↔ média

Les rôles `primary`, `poster` et `fallback` sont uniques par question dans l'API Phase 3. Plusieurs médias `explanation` peuvent être attachés avec `display_order`.

L'association ne modifie pas les champs `Question.media_*`. Cela garantit qu'une question de production continue à utiliser le mécanisme historique tant que la Phase 5 n'a pas installé le resolver de compatibilité.

## Audit

Les opérations suivantes créent une entrée d'audit :

- création média ;
- mise à jour média ;
- archivage ;
- association à une question ;
- retrait d'une association.

Les entrées ne stockent pas de credentials de provider.

## Codes d'erreur

- `401/403` : authentification/RBAC ;
- `404` : média/question/association absent ;
- `409` : checksum déjà présent, rôle déjà occupé, média archivé ;
- `422` : URL/MIME/checksum/référence/provider invalide ;
- `503` : storage provider demandé mais non configuré ou indisponible.

## CI

Le workflow `National Code Readiness` contient un job `media-library` qui compile la Media Factory et exécute :

- migrations ;
- modèles MediaAsset ;
- policy image/video/audio ;
- storage providers ;
- validation de métadonnées ;
- API médiathèque et associations.

## Ce que la Phase 3 ne fait pas encore

Elle ne :

- valide pas pédagogiquement un média ;
- homologue pas un média DNTT ;
- bloque encore la publication d'une question selon `MediaAsset` ;
- remplace pas les SVG legacy ;
- change pas le player de l'examen ;
- migre pas les 200 questions existantes.

Ces points appartiennent aux phases suivantes du plan média premium.
