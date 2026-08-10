# Phase 1 — Exécution de l'audit média

Cette phase est volontairement **non fonctionnelle** : elle ne modifie ni la base, ni les endpoints, ni l'interface candidat, ni les règles d'examen.

## Fichiers ajoutés

- `docs/media/MEDIA_AUDIT.md` : audit architectural et qualitatif.
- `scripts/audit_media_library.py` : inventaire read-only de la banque réellement présente en base.
- `backend/tests/test_media_audit_script.py` : tests de classification de l'audit.

## Commande de recette

Depuis la racine :

```bash
python scripts/audit_media_library.py --json media-audit.json
```

Pour sonder les URLs image/vidéo réelles :

```bash
python scripts/audit_media_library.py --probe-remote --json media-audit.json
```

Le probing distant reste optionnel et passe par la politique URL existante avant toute requête.

## Frontière de non-régression

Phase 1 n'autorise pas :
- migration BDD ;
- modification du modèle Question ;
- remplacement automatique d'un média ;
- suppression d'un SVG legacy ;
- changement du player ;
- modification du scoring/exam engine ;
- changement de validation DNTT ;
- changement de `render.yaml`.

La Phase 2 pourra commencer uniquement à partir du modèle normalisé `MediaAsset` / `QuestionMedia` avec une migration additive et rétrocompatible.
