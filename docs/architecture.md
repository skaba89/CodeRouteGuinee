# Architecture - CodeRoute Guinee

## Vue logique

- Frontend React pour les candidats, centres, auto-ecoles et administrateurs.
- API FastAPI pour exposer les services metier.
- PostgreSQL pour les donnees transactionnelles.
- Stockage objet futur pour photos, pieces d'identite et certificats.
- Module BI futur pour statistiques nationales.

## Domaines metier

- Identity : utilisateurs, roles, permissions.
- Candidate : dossiers candidats.
- Center : centres agrees, salles et postes.
- Exam : questions, sessions, tentatives, reponses.
- Audit : traces, incidents, alertes.
- Payment : paiements et recus.

## Principes

- API-first.
- RBAC des le MVP.
- Traçabilite forte.
- Donnees structurees pour reporting national.
- Architecture evolutive vers mobile, paiement et permis biometrique.
