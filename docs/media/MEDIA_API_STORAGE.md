# CodeRoute Guinée — Phase 3 API média et stockage

Cette branche est volontairement ouverte en Draft avant les changements applicatifs afin d'empêcher un auto-merge partiel.

Objectifs de la phase :
- API de médiathèque indépendante de `Question.media_*` ;
- création/lecture/mise à jour/archivage des métadonnées média ;
- association `QuestionMedia` sans modifier encore le rendu examen ;
- validation serveur de l'URL, du MIME, de la taille et du checksum ;
- abstraction de stockage configurable ;
- réutilisation du flux Cloudinary signé existant ;
- préparation S3-compatible (AWS S3 / Cloudflare R2 / MinIO) sans exposition des credentials ;
- invalidation fail-closed des validations lors d'un changement sensible du média.

Les workflows de validation pédagogique/réglementaire et le quality gate de publication restent en Phase 4.
