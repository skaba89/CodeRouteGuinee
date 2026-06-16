# Revue manuelle des tentatives signalees

Ce module permet a l'administration de prendre une decision formelle sur une tentative d'examen signalee par les mecanismes de supervision.

## Objectif

Apres detection d'un risque, l'administration doit pouvoir :

- consulter le dossier de revue d'une tentative ;
- voir le score et les evenements de surveillance ;
- prendre une decision officielle ;
- tracer cette decision dans l'audit national.

## Decisions disponibles

- `clear` : la tentative est revue et consideree acceptable.
- `invalidate` : la tentative est invalidee.
- `require_retake` : une nouvelle tentative doit etre organisee.

## Effet sur la tentative

- `clear` met la tentative en statut `review_cleared`.
- `invalidate` met la tentative en statut `invalidated` et force `passed=false`.
- `require_retake` met la tentative en statut `retake_required` et force `passed=false`.

## Endpoints

- `POST /api/v1/exam-reviews/decisions` : creer une decision de revue.
- `GET /api/v1/exam-reviews/attempts/{attempt_id}` : consulter le dossier de revue d'une tentative.
- `GET /api/v1/exam-reviews/decisions` : lister les decisions.

## Audit

Chaque decision cree un audit log :

- `exam_review.clear` ;
- `exam_review.invalidate` ;
- `exam_review.require_retake`.

## Test E2E

```bash
pytest backend/tests/test_e2e_manual_review_decisions.py
```
