# Monitoring exploitation

Ce module donne une vue courte de supervision nationale pour la DSI, les administrateurs et les responsables metier.

Endpoint protege:

```text
GET /api/v1/operations/summary
```

Roles autorises:

- `admin`
- `super_admin`

Signaux consolides:

- incidents centre ouverts et incidents critiques;
- evenements examen `high` et `critical`;
- appareils ou postes suspects;
- alertes financieres de rapprochement;
- activite du journal d'audit sur les dernieres 24h.

Statuts:

- `ok` : aucune alerte warning ou critique;
- `warning` : au moins une alerte a traiter;
- `critical` : un seuil critique est atteint.

Chaque consultation est journalisee dans `audit_logs` avec l'action:

```text
operations.summary_viewed
```

Controle avant production:

1. Se connecter avec un compte `admin` ou `super_admin`.
2. Ouvrir le cockpit admin, section `Exploitation`.
3. Verifier que les alertes pointent vers les sections de traitement: incidents, finance, monitoring examen ou audit.
4. Exporter le journal d'audit si une anomalie critique est presente.
