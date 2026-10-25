---
name: exam-feature-validation
description: Validation d'une fonctionnalité d'examen CodeRoute (tirage, écran d'épreuve, notation, multi-réponses, médias, reprise, incidents, publication des résultats) avant PR — confidentialité, intégrité, équité, règles non inventées, résilience.
---

# Validation d'une fonctionnalité d'examen

Cocher chaque point avec sa preuve (test ou exécution).

1. **Confidentialité** : invariants I1, I2 et I10 (`docs/audit/PLAN_TESTS_EXAMEN.md`) verts.
2. **Trace** : la tentative reste notée sur sa trace (questions, révisions, règle figées au démarrage).
3. **Chronométrage** : aucune réponse acceptée après l'échéance ; le temps suspendu pour incident n'est pas décompté.
4. **Reprise** : rafraîchissement, changement de poste et coupure réseau courte ne perdent aucune réponse synchronisée (`test_exam_runtime_recovery.py`, `exam-runtime-resilience.spec.ts`).
5. **Idempotence** : soumission et finalisation rejouables sans double effet.
6. **Règles** : tout paramètre (nombre, seuil, durée, répartition, publication) vient de la configuration ou de la règle versionnée, marqué provisoire s'il n'est pas homologué (R1-R20).
7. **Équité** : répartition par thème exacte ; un incident ne pénalise pas le candidat.
8. **Accessibilité et débit** : utilisable au clavier, lisible à 360 px, médias préchargés.
9. **Hors-ligne centre** : comportement défini avec la passerelle edge (ou explicitement hors périmètre).
10. **Répétition** : `scripts/demo.sh check` vert.

Sortie : tableau des 10 points (OK / KO / N.A.), avec preuves.
