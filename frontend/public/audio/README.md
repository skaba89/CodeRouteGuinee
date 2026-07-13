# Enregistrements audio — langues nationales

Déposez ici les enregistrements des questions par des locuteurs natifs.

## Convention

    audio/<langue>/<numero>.mp3

Codes de langue :
  ff   Pular
  man  Malinké
  sus  Soussou
  kss  Kissi
  gkp  Kpelle
  lom  Toma

Exemple : `audio/ff/1.mp3` = question 1 enregistrée en Pular.

## Rappel de conception

Seul l'ORAL est en langue nationale. Le texte des questions reste affiché
en français. Le candidat VOIT la question en français et l'ENTEND dans sa
langue.

## Import

Après avoir déposé les fichiers :

    python scripts/import_audio.py --from-dir frontend/public/audio

Vérifier la couverture à tout moment :

    python scripts/import_audio.py --report

Les questions sans enregistrement utilisent la synthèse vocale du
navigateur (repli automatique) — aucune question n'est jamais muette.

Voir `docs/audio_langues_nationales.md` pour le guide complet.
