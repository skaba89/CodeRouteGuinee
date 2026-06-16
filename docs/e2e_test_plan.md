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

## Parcours examen resultat certificat

- Demarrer une tentative d'examen.
- Soumettre les reponses.
- Verifier le scoring et le statut de reussite.
- Refuser une double soumission.
- Generer le certificat PDF.
- Verifier publiquement le certificat.
- Controler le resume national des examens.

## Parcours candidat complet

- Creer un centre agree et une session.
- Ajouter les questions de reference.
- Inscrire un candidat.
- Creer une reservation.
- Verifier la convocation et le QR code.
- Executer le paiement.
- Valider l'entree centre.
- Demarrer et soumettre l'examen.
- Verifier le certificat et telecharger le PDF.

## Parcours a completer ensuite

- Incidents centre et reprise d'examen.
- Tests UI navigateur via Playwright.
- Tests de charge et monitoring.
