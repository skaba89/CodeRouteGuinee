# Recette examen multimedia 40 questions

Cette recette valide un parcours candidat complet dans un centre agree avec une banque de 40 questions illustrees.

## Scenario couvert

1. Import du centre pilote en simulation puis en ecriture.
2. Import du candidat verifie en simulation puis en ecriture.
3. Import de 40 questions officielles avec alternance images/videos.
4. Verification que l API restitue les champs `media_type`, `media_url` et `media_alt`.
5. Creation d une session dans le centre.
6. Reservation du candidat dans cette session.
7. Generation de la convocation.
8. Validation entree centre avec code de verification.
9. Demarrage examen depuis la reservation avec trace appareil.
10. Soumission des reponses.
11. Verification du certificat.
12. Controle du suivi via resume examen et audit de trace des questions.

## Commande

Depuis le dossier `backend`:

```bash
pytest tests/test_e2e_candidate_center_multimedia_exam.py
```

## Criteres d acceptation

- Les 40 questions sont importees.
- 20 questions contiennent une image et 20 contiennent une video.
- Chaque question multimedia a une URL et une description.
- Le candidat est reserve dans un centre agree.
- L entree centre est autorisee.
- L examen est soumis avec succes.
- Le certificat est verifiable.
- La trace d examen indique au moins 40 questions snapshottees.
