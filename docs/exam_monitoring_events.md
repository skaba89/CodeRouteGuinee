# Evenements de surveillance d'examen

Ce module ajoute une couche de supervision anti-fraude pendant les examens du code de la route.

## Objectif

Tracer les evenements techniques ou comportementaux observes pendant une tentative d'examen, puis calculer un niveau de risque pour aider l'administration nationale a prioriser les controles.

## Exemples d'evenements

- `heartbeat_delay` : retard de communication avec le poste d'examen.
- `fullscreen_exit` : sortie du plein ecran pendant l'examen.
- `tab_switch` : changement d'onglet ou perte de focus.
- `connection_drop` : coupure reseau.
- `manual_note` : remarque saisie par un superviseur.

## Scores de risque

- `low` : 1 point.
- `medium` : 3 points.
- `high` : 7 points.
- `critical` : 12 points.

## Statuts de synthese

- `normal` : moins de 4 points.
- `watch` : de 4 a 9 points.
- `manual_review` : de 10 a 19 points.
- `critical_review` : 20 points ou plus.

## Endpoints

- `POST /api/v1/exam-monitoring/events` : enregistrer un evenement.
- `GET /api/v1/exam-monitoring/events` : lister les evenements avec filtres.
- `GET /api/v1/exam-monitoring/attempts/{attempt_id}/summary` : obtenir le resume de risque d'une tentative.
- `GET /api/v1/exam-monitoring/summary` : lister les resumes de risque.

## Audit

Les evenements sont journalises dans le module de supervision :

- `exam_monitoring.event_recorded` pour les evenements standards.
- `exam_monitoring.high_risk_event` pour les evenements `high` ou `critical`.

## Test E2E

```bash
pytest backend/tests/test_e2e_exam_monitoring_events.py
```
