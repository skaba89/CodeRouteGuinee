# Securite et anti-fraude

## Objectif

Garantir que chaque examen est passe par le bon candidat, dans un centre agree, selon une session autorisee, avec correction fiable et resultat verifiable.

## Mesures MVP

- Convocation avec reference unique.
- Verification du candidat a l'entree du centre.
- Journalisation du demarrage et de la soumission de l'examen.
- Questions tirees aleatoirement.
- Ordre des reponses melange dans une version future.
- Resultat reference et historise.
- Limitation des tentatives de connexion par email/IP.
- Audit des connexions reussies, echouees et bloquees.
- Headers HTTP de securite sur les reponses API.
- Gouvernance des comptes avec changement de role et suspension reserves au `super_admin`.

## Mesures avancees

- Photo le jour de l'examen.
- Comparaison avec la photo du dossier.
- Webcam monitoring.
- Detection de taux de reussite anormaux.
- Audit des centres.
- Suspension automatique apres incident grave.
- Signature numerique des resultats.
