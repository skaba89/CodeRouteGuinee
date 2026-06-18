# Recette pilote institutionnelle

Cette recette valide le parcours complet avec des donnees officielles simulees avant une presentation ou une mise en recette.

## Scenario couvert

1. Connexion admin.
2. Import centre officiel en simulation (`dry_run=true`).
3. Import centre officiel reel.
4. Import candidat officiel en simulation.
5. Import candidat officiel reel.
6. Import de 40 questions officielles en simulation.
7. Import reel de la banque de questions.
8. Creation session et reservation.
9. Import paiement operateur en simulation.
10. Import paiement operateur reel.
11. Telechargement convocation PDF.
12. Controle entree centre.
13. Demarrage examen depuis la reservation avec trace appareil.
14. Soumission des reponses.
15. Verification certificat.
16. Controle du resume exploitation.
17. Controle des logs d'audit.

## Commande

Depuis le dossier `backend`:

```bash
pytest tests/test_e2e_institutional_pilot_recipe.py
```

## Criteres d'acceptation

- Les simulations ne creent aucune donnee.
- Les imports reels creent les donnees attendues.
- Le paiement officiel est rapproche avec la reservation.
- La convocation PDF commence par `%PDF`.
- L'entree centre est autorisee avec le code de verification.
- L'examen est soumis avec resultat positif.
- Le certificat verifie retourne le candidat et le centre attendus.
- `/api/v1/operations/summary` retourne une activite d'audit recente.
- Les actions d'audit incluent les imports officiels candidats, centres, questions et paiements.

## Usage presentation Etat

Cette recette peut etre presentee comme preuve de maturite pilote: donnees officielles controlees, parcours candidat complet, paiement rapproche, attestation verifiable et audit national.
