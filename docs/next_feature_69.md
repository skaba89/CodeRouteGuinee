# Next feature 69

Ce module ajoute un flux de suivi administratif rattache a une tentative d'examen.

## Capacites

- creer un message rattache a un candidat et une tentative ;
- lister les messages cote administration ;
- traiter le message avec un statut officiel ;
- conserver une trace dans les logs d'audit.

## Endpoints

- `POST /api/v1/candidate-submissions`
- `GET /api/v1/candidate-submissions`
- `POST /api/v1/candidate-submissions/{submission_id}/handle`

## Statuts

- `submitted`
- `under_review`
- `accepted`
- `rejected`
- `retake_planned`

## Test

```bash
pytest backend/tests/test_e2e_candidate_submissions.py
```
