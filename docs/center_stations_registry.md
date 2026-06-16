# Registre des postes d'examen par centre

Ce module permet de declarer les postes officiels autorises pour chaque centre d'examen.

## Objectif

Renforcer la supervision nationale en distinguant :

- un poste connu et autorise ;
- un poste inconnu ;
- un poste desactive ou en maintenance.

## Endpoints

- `POST /api/v1/center-stations` : declarer un poste.
- `GET /api/v1/center-stations` : lister les postes.
- `PATCH /api/v1/center-stations/{station_id}` : modifier le libelle, la salle ou le statut.

## Statuts

- `active` : poste autorise.
- `disabled` : poste desactive.
- `maintenance` : poste temporairement indisponible.

## Controle automatique

Lorsqu'un centre possede au moins un poste actif declare, le endpoint :

`POST /api/v1/device-sessions/heartbeat`

controle le `device_key` entrant.

Si le poste n'est pas declare, la session appareil devient :

- `status = suspicious`
- `risk_reason = unregistered_center_station`

Un audit log est cree avec l'action :

- `device_session.station_alert`

## Test E2E

```bash
pytest backend/tests/test_e2e_center_stations_registry.py
```
