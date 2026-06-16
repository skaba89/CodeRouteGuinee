# E2E parcours candidat complet

Cette suite valide le parcours national de bout en bout : creation centre/session, questions, candidat, reservation, convocation, QR code, paiement, entree centre, examen, certificat et PDF.

## Objectif

Garantir que le flux principal de CodeRoute Guinee reste fonctionnel avant une demonstration ou une mise en recette.

## Commande

```bash
pytest backend/tests/test_e2e_candidate_full_flow.py
```

## Couverture

- Creation d'un centre agree et d'une session.
- Creation des questions de reference.
- Inscription d'un candidat.
- Reservation d'une session.
- Verification de la convocation et du QR code.
- Paiement Mobile Money sandbox.
- Controle d'entree centre.
- Demarrage et soumission de l'examen.
- Verification du certificat et du PDF resultat.
