# Code readiness vs go-live evidence

This repository separates automated code readiness from operational and institutional go-live evidence.

## Automated gates

The CI suites validate the implementation supporting:

- P10.2: HA configuration, readiness/liveness, reliability evidence, encrypted/off-region backup tooling, restore/failover probes and observability guards;
- P11: SOC configuration, privacy/pseudonymisation, HMAC audit-chain integrity, runtime security guards and security observability;
- P12: national policy governance, four-eyes approval rules, technical-policy alignment and homologation dossier completeness;
- frontend: locked dependencies, high/critical npm audit, typecheck, production build and critical browser E2E flows.

## Evidence that CI must never fabricate

A green code suite does **not** prove production operations or government approval. The following require real evidence from the target environment or the responsible institution:

- successful off-region restore/PITR and measured RPO/RTO;
- real API failover and observability/alert delivery;
- provisioned SOC keys, SIEM/OTLP ingestion, WAF/DDoS controls and operational incident drills;
- DNTT/legal validation of the official exam policy and content rights;
- named approvers, signed evidence and final homologation decision.

Issues tracking those go-live proofs must remain open until the corresponding runtime/institutional evidence exists, even when the implementation tests are green.
