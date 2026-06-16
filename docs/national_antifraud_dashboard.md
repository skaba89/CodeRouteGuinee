# Tableau de bord national anti-fraude

Ce module consolide les signaux anti-fraude de CodeRoute Guinee dans une vue nationale exploitable par les administrateurs.

## Objectif

Donner a l'administration nationale une vision immediate des centres et tentatives a surveiller, en croisant :

- les incidents centre ouverts ;
- les appareils de session suspects ;
- les evenements de surveillance d'examen ;
- les scores de risque agreges.

## Endpoint

`GET /api/v1/dashboard/anti-fraud`

Acces reserve aux roles :

- `admin` ;
- `super_admin`.

## Indicateurs exposes

- `open_center_incidents` : nombre d'incidents centre ouverts.
- `suspicious_device_sessions` : nombre de sessions appareil suspectes.
- `high_risk_monitoring_events` : evenements de surveillance de niveau high.
- `critical_monitoring_events` : evenements de niveau critical.
- `total_monitoring_risk_score` : somme des scores de surveillance.
- `manual_review_attempts` : tentatives dont le score impose une revue manuelle.
- `centers_at_risk` : centres classes par score de risque.

## Score centre

Le score d'un centre combine :

- score des evenements de surveillance ;
- incidents ouverts, ponderes a 5 points ;
- appareils suspects, ponderes a 4 points.

## Statuts

- `normal` : score inferieur a 5 ;
- `watch` : score de 5 a 14 ;
- `manual_review` : score de 15 a 29 ;
- `critical_review` : score de 30 ou plus.

## Test E2E

```bash
pytest backend/tests/test_e2e_antifraud_dashboard.py
```
