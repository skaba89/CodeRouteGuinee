# CodeRoute Guinée — Phase 4 quality gate et validation média

## Objet

Cette phase installe le workflow humain et le back-office de la médiathèque premium. Elle ne remplace pas encore le renderer candidat : le basculement de lecture vers `MediaAsset` appartient à la Phase 5.

Règle de compatibilité : les questions historiques qui n'ont pas encore de `QuestionMedia(primary)` restent compatibles jusqu'à la Phase 7. Dès qu'une question utilise un média principal normalisé, son approbation officielle est bloquée tant que ce média ne satisfait pas le quality gate et la validation réglementaire.

## Quality score

`backend/app/media_quality.py` calcule un score technique et de traçabilité sur 100 sans jamais inventer une validation humaine.

Pour un média d'examen, le gate contrôle notamment :

- média non archivé ;
- `usage_type=exam` ;
- URL de livraison durable ;
- SHA-256 ;
- MIME autorisé ;
- résolution minimum 1280x720 pour image/vidéo ;
- ratio lisible sur mobile ;
- durée vidéo comprise entre 6 et 20 secondes ;
- poster image validé pour vidéo ;
- fallback image validé pour vidéo ;
- provenance traçable ;
- licence/droits traçables et non expirés ;
- `quality_status=validated` ;
- `regulatory_status=validated` avec référence d'autorité lorsque la publication officielle est demandée.

Un contenu `generated` ou `legacy` ne passe pas automatiquement le gate d'un média principal d'examen officiel. Les contenus générés restent utilisables dans les usages pédagogiques/corrections après revue appropriée, mais ne sont pas transformés automatiquement en contenu officiel.

## Quatre yeux

Le créateur d'un média ne peut pas effectuer sa validation finale.

Workflow qualité :

1. création → `draft` ;
2. soumission qualité → `review_required` ;
3. approbation par un autre `admin`/`super_admin` → `validated` ;
4. ou rejet → `rejected`.

Workflow réglementaire :

1. qualité déjà `validated` ;
2. soumission → `under_review` ;
3. approbation par un `super_admin` différent du créateur ;
4. référence d'autorité obligatoire ;
5. résultat → `validated` ou `rejected`.

Les actions sont historisées dans `AuditLog`.

## Aucun faux statut DNTT

La plateforme ne décide pas qu'une référence est juridiquement valable. Elle exige seulement qu'une référence d'autorité soit fournie pour le statut réglementaire final.

Une référence telle que `DNTT-MEDIA-...` utilisée dans les tests est une donnée de test, pas une preuve institutionnelle réelle.

L'homologation nationale reste une décision humaine/institutionnelle séparée.

## Invalidation automatique

Une modification sensible d'un média déjà validé invalide les validations précédentes.

Exemples :

- checksum ;
- fichier/URL ;
- MIME ;
- dimensions/durée ;
- provider/storage key ;
- poster/fallback ;
- pays/périmètre réglementaire ;
- source ;
- licence ;
- copyright.

Le média revient alors vers :

- `quality_status=review_required` ;
- `regulatory_status=under_review` ;
- `validated_by=null` ;
- `validated_at=null`.

## Gate sur l'approbation d'une question

Le contrôle est installé au niveau SQLAlchemy `before_flush` afin de protéger toutes les voies applicatives qui effectuent une vraie transition de `Question.validation_status` vers `approved`.

### Question legacy

Aucun `QuestionMedia(primary)` :

- compatibilité temporaire ;
- l'approbation existante reste possible ;
- le résultat du gate indique `legacy_migration_required=true`.

Cette exception disparaîtra uniquement après le backfill contrôlé de la Phase 7.

### Question normalisée

Présence de `QuestionMedia(primary)` :

- le média doit passer le gate complet ;
- sinon la transaction est bloquée ;
- l'API renvoie `409 MEDIA_QUALITY_GATE_BLOCKED` avec les blockers détaillés.

## Back-office

Route frontend :

`#/admin/media-library`

Accès :

- `admin` ;
- `super_admin`.

Fonctions principales :

- grille des médias ;
- recherche et filtres type/qualité/réglementaire ;
- aperçu image/vidéo/audio ;
- dimensions/durée ;
- SHA-256 ;
- source/licence/copyright ;
- quality score ;
- blockers ;
- upload direct ;
- soumission qualité ;
- validation/rejet qualité ;
- soumission réglementaire ;
- validation/rejet réglementaire ;
- archivage.

## Upload sécurisé

Le navigateur :

1. calcule SHA-256 localement ;
2. mesure les dimensions/durée du fichier ;
3. demande au backend une cible d'upload courte durée ;
4. envoie directement le fichier au provider ;
5. enregistre ensuite les métadonnées finales dans `MediaAsset`.

Les credentials longue durée ne sont jamais envoyés au navigateur.

### Cloudinary

Le provider retourne lui-même l'URL finale après upload.

### S3 / R2 / MinIO

L'URL PUT pré-signée est séparée de l'URL durable de lecture.

Variables importantes :

- `MEDIA_S3_BUCKET` ;
- `MEDIA_PUBLIC_BASE_URL` ;
- `MEDIA_S3_PREFIX` ;
- `MEDIA_S3_ENDPOINT_URL` ;
- `MEDIA_S3_REGION` ;
- credentials serveur S3 compatibles.

`MEDIA_PUBLIC_BASE_URL` doit être HTTPS. Une URL pré-signée temporaire n'est jamais enregistrée comme URL média d'examen.

## CI

`National Code Readiness` protège désormais :

- compilation de la Media Factory ;
- migrations ;
- tous les `backend/tests/test_media_*.py` ;
- audit npm high/critical ;
- TypeScript ;
- build production ;
- E2E `media-library.spec.ts` ;
- E2E Edge/SOC/P12 déjà existants.

## Limites de Phase 4

Cette phase ne :

- remplace pas les SVG legacy dans l'examen ;
- ne migre pas encore les 200 questions ;
- ne choisit pas automatiquement les bons médias réels ;
- ne crée aucune preuve institutionnelle ;
- ne modifie pas encore `ExamMediaPremium` pour lire `QuestionMedia`.

La Phase 5 peut maintenant implémenter le resolver média normalisé + fallback legacy dans l'expérience candidat.
