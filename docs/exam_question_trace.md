# Traçabilité du questionnaire d'examen

Ce module crée une trace officielle du questionnaire utilisé pour chaque tentative d'examen.

## Objectif

Garantir que l'administration peut vérifier, après coup :

- quelles questions étaient attachées à une tentative ;
- combien de questions étaient présentes dans la banque active ;
- le hash de version de la banque utilisée ;
- le mode de sélection appliqué.

## Création de la trace

Lors de l'appel :

`POST /api/v1/exams/start`

la plateforme capture les questions actives et crée une ligne `exam_question_traces`.

Chaque trace contient :

- `attempt_id` ;
- `question_ids` ;
- `question_count` ;
- `bank_hash` ;
- `version_label` ;
- `selection_mode` ;
- `created_at`.

Si aucune question active n'existe, la tentative peut toujours démarrer et la trace porte le label `active-bank-empty`.

## Consultation admin

- `GET /api/v1/exam-question-traces/attempts/{attempt_id}`
- `GET /api/v1/exam-question-traces`

Ces endpoints sont réservés aux rôles `admin` et `super_admin`.

## Audit

Chaque démarrage d'examen crée un log :

- `exam.question_trace_created`

## Test E2E

```bash
pytest backend/tests/test_e2e_exam_question_trace.py
```
