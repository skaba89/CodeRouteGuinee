# P10.2 — Preuve PITR fournisseur

## Principe

CodeRoute ne fournit pas lui-même le Point-In-Time Recovery PostgreSQL. Le PITR reste une capacité du fournisseur de base de données et doit être réellement activé et testé. Cette extension ajoute uniquement un **contrat de preuve auditable**.

La cible P10.2 reste :

- RPO observé ≤ 5 minutes ;
- RTO observé ≤ 30 minutes.

Une preuve `pitr_drill_passed` n'est acceptée que si les deux valeurs mesurées respectent les cibles configurées (`DR_RPO_MINUTES`, `DR_RTO_MINUTES`).

## Pièce externe obligatoire

Le rapport fournisseur/opérateur doit être archivé hors Git dans la GED/coffre de preuves. La preuve machine ne stocke pas le document ; elle stocke :

- sa référence interne ;
- son SHA-256 ;
- la date/heure réelle du test ;
- le RPO mesuré ;
- le RTO mesuré.

Les URL, credentials et références contenant `@` sont refusés par l'API de preuve.

## Reçu supporté

`publish_reliability_evidence.py` accepte :

```json
{
  "kind": "coderoute_pitr_drill_receipt_v1",
  "passed": true,
  "finished_at": "2026-08-09T18:30:00+00:00",
  "evidence_sha256": "<sha256-du-rapport>",
  "reference": "PITR-DRILL-2026-08-09",
  "observed_rpo_minutes": 3.2,
  "observed_rto_minutes": 17.0
}
```

Puis :

```bash
export CODEROUTE_API_BASE_URL="https://coderouteguinee-backend.onrender.com"
export RELIABILITY_EVIDENCE_TOKEN="<secret-m2m>"
python backend/scripts/publish_reliability_evidence.py /secure/receipts/pitr.json
unset RELIABILITY_EVIDENCE_TOKEN
```

Le backend refuse un reçu marqué réussi dont le RPO/RTO dépasse la politique courante.

## Freshness

La politique d'exploitation initiale retient **35 jours** comme fraîcheur maximale du dernier drill PITR réussi, alignée sur les drills restore/failover P10.2. Ce seuil est contrôlé :

- dans le Go-Live Evidence Pack (`P10_PITR_FRESH`) ;
- par Prometheus (`CodeRoutePITREvidenceStale`) ;
- dans la readiness nationale P12 (`pitr_provider`).

## Ce que la preuve ne démontre pas seule

Un AuditLog `reliability.pitr_drill_passed` ne remplace pas :

- la capture/preuve fournisseur que PITR est activé ;
- la rétention configurée ;
- le rapport du test de restauration à timestamp ;
- la validation de responsabilité fournisseur/DNTT ;
- l'archivage de la pièce externe correspondant au SHA-256.

La fermeture de #134 exige donc la pièce externe en plus de la preuve machine.