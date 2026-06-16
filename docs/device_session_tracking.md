# Tracabilite des appareils de session

Ce module renforce la supervision anti-fraude en journalisant les appareils utilises pendant les sessions d'examen.

## Objectif

Identifier les postes d'examen utilises dans un centre, suivre leur activite et detecter les usages suspects, par exemple le meme appareil associe a plusieurs tentatives pendant une meme session.

## Regles metier

- Un agent centre, un admin ou un super admin peut envoyer un heartbeat d'appareil.
- Chaque heartbeat reference un centre, une session, un identifiant d'appareil et optionnellement une tentative.
- Si le meme appareil est associe a plusieurs tentatives actives dans la meme session, les lignes concernees sont marquees `suspicious`.
- Les doublons suspects creent un audit log `device_session.suspicious_duplicate`.
- Les admins peuvent consulter la liste des appareils et les alertes.

## Endpoints

- `POST /api/v1/device-sessions/heartbeat` : enregistrer ou mettre a jour l'activite d'un appareil.
- `GET /api/v1/device-sessions` : lister les appareils, avec filtres par centre, session et statut.
- `GET /api/v1/device-sessions/alerts` : lister les appareils suspects.

## Test E2E

```bash
pytest backend/tests/test_e2e_device_session_tracking.py
```

Le scenario valide : creation d'un centre, d'une session, de deux tentatives, puis detection d'un meme appareil utilise pour deux tentatives distinctes.
