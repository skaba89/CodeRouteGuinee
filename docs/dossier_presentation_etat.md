# Dossier de presentation Etat - CodeRoute Guinee

## Resume executif

CodeRoute Guinee est une plateforme nationale pour digitaliser le parcours du code de la route : inscription candidat, reservation, paiement, convocation, controle d entree en centre, examen securise, resultats, certificats, supervision et audit.

L objectif est de fournir a l Etat guineen un dispositif pilotable, traçable et extensible pour harmoniser les examens, reduire les fraudes, suivre les centres agrees et produire des indicateurs nationaux fiables.

## Problemes adresses

- Files et processus manuels difficiles a superviser.
- Manque de visibilite nationale sur les centres et sessions.
- Risques de fraude sur l identite, l entree en centre et la correction.
- Resultats et attestations difficiles a verifier rapidement.
- Absence de reporting consolide pour les decisions publiques.

## Solution proposee

- Portail candidat pour le dossier, la reservation, le paiement, la convocation et les resultats.
- Interface centre pour verifier les entrees et suivre les sessions.
- Console admin nationale pour superviser centres, identites, questions, paiements, audit et habilitations.
- Examen numerique avec suivi de session, score et certificat verifiable.
- Tableau de bord institutionnel avec maturite, actions prioritaires, securite, conformite et feuille de route.

## Gouvernance

- Roles separes : candidat, centre, admin national, super admin.
- Habilitations institutionnelles pour encadrer conventions, autorisations et decisions.
- Journal d audit pour les actions sensibles.
- Exports CSV pour reporting administratif et controle.

## Securite et conformite

- Controle d acces par role.
- Sessions et actions sensibles journalisees.
- Verification administrative des identites.
- Controle d entree centre par reference et code.
- Certificats numeriques verifiables.
- Matrice de securite couvrant acces, tracabilite, antifraude et donnees personnelles.

## Architecture cible

- Frontend React pour les interfaces candidat, centre et administration.
- API FastAPI pour les services metier.
- Base PostgreSQL pour les donnees transactionnelles.
- Stockage objet cible pour photos, pieces d identite et certificats.
- Monitoring, sauvegardes et CI/CD a mettre en place pour la production.

## Calendrier pilote propose

| Periode | Objectif |
| --- | --- |
| Semaine 1-2 | Validation ministerielle du perimetre pilote et des centres retenus. |
| Semaine 3-4 | Import des donnees officielles, formation agents et tests en centre. |
| Mois 2 | Pilote controle avec candidats reels, supervision nationale et rapport hebdomadaire. |
| Mois 3 | Bilan, corrections et extension progressive vers les regions prioritaires. |

## Points restants avant production

1. Brancher les registres officiels candidats, centres et pieces d identite.
2. Importer la banque nationale de questions par categorie de permis.
3. Renforcer l antifraude : photo candidat, surveillance centre, anomalies horodatees.
4. Finaliser les politiques de conservation, consentement et acces aux donnees sensibles.
5. Industrialiser l hebergement : staging, production, sauvegardes, monitoring, secrets.
6. Completer les tests API, E2E et securite.
7. Produire la presentation officielle, le budget pilote et le plan de conduite du changement.

## Decision attendue

Valider un pilote institutionnel encadre avec centres retenus, donnees officielles limitees, supervision nationale et rapport de fin de pilote permettant de decider l extension progressive.
