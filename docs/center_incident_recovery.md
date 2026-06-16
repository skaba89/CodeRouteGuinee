# Incidents centre et reprise d'examen

Ce module couvre les interruptions terrain pendant une session d'examen : coupure de courant, panne reseau, poste indisponible, probleme de supervision ou autre incident qui rend la tentative initiale non fiable.

## Objectif national

Garantir qu'un incident centre ne produise ni fraude, ni double soumission, ni perte de tracabilite.

## Regles metier

- Un agent centre, un admin national ou un super admin peut declarer un incident.
- Si l'incident est lie a une tentative en cours, la tentative passe de `started` a `incident_blocked`.
- Une tentative `incident_blocked` ne peut plus etre soumise.
- Seul un admin ou super admin peut resoudre l'incident.
- Si la reprise est autorisee, l'ancienne tentative passe a `cancelled_by_incident` et une nouvelle tentative `started` est creee.
- Chaque declaration et resolution est tracee dans les logs d'audit.

## Endpoints

- `POST /api/v1/center-incidents` : declarer un incident centre.
- `GET /api/v1/center-incidents` : lister les incidents, filtre possible par `status_filter` et `center_id`.
- `POST /api/v1/center-incidents/{incident_id}/resolve` : resoudre un incident et autoriser ou non une reprise.

## Test E2E

```bash
pytest backend/tests/test_e2e_center_incident_recovery.py
```

Le scenario valide :

1. creation d'un centre agree ;
2. creation d'une session et de questions ;
3. inscription d'un candidat ;
4. demarrage d'une tentative ;
5. declaration d'un incident par le centre ;
6. blocage de la tentative initiale ;
7. resolution admin avec reprise autorisee ;
8. creation d'une nouvelle tentative ;
9. soumission reussie de la nouvelle tentative ;
10. verification des logs d'audit.
