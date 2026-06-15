# Plan de tests E2E CodeRoute Guinee

Ce plan couvre les parcours critiques de la plateforme nationale.

## Parcours admin finance

- Creer un administrateur de test.
- Se connecter avec JWT.
- Alimenter des paiements representatifs.
- Consulter le resume financier filtre.
- Consulter les lignes de rapprochement.
- Consulter les alertes financieres.
- Exporter les paiements en CSV.
- Verifier la presence des logs d'audit.

## Parcours candidat reservation et centre

- Creer un candidat.
- Creer une reservation sur une session.
- Declencher un paiement Mobile Money sandbox.
- Recuperer la convocation numerique.
- Generer la convocation PDF.
- Valider l'entree dans un centre agree.
- Refuser une deuxieme entree deja consommee.

## Parcours a completer ensuite

- Examen : demarrage, soumission, scoring et anti-fraude.
- Resultats : certificat PDF et verification publique.
