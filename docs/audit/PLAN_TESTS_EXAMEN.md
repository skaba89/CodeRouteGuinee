# Plan de tests de l'examen

> Socle existant : 1 302 tests pytest (SQLite, suite bloquante en CI, couverture
> 84 %) et 21 specs Playwright. Ce plan liste les **tests à ajouter** pour chaque
> évolution de la feuille de route, et les invariants qui ne doivent jamais régresser.

## 1. Invariants (non-régression permanente)

| ID | Invariant | Test existant |
|---|---|---|
| I1 | Aucune réponse correcte, explication ou clé dans une réponse d'API candidat ou centre pendant l'épreuve | `test_exam_bank_confidentiality.py` |
| I2 | Le résultat candidat ne contient pas `correct_answer` | `test_exam_bank_confidentiality.py` |
| I3 | Une tentative ne se note que sur sa trace officielle | `test_e2e_exam_question_trace.py` |
| I4 | Aucune réponse acceptée après l'échéance | `test_exam_runtime_recovery.py` |
| I5 | Une soumission est idempotente | `test_exam_flow.py` |
| I6 | Aucune question d'entraînement dans le pool officiel | `test_exam_engine.py` |
| I7 | Un agent n'agit que sur son centre | `test_entries_coverage.py` |
| I8 | Le journal d'audit reste vérifiable et détecte toute altération | `test_dr_readiness.py` |
| I9 | Pas d'examen sans identité vérifiée, paiement, check-in, poste enregistré | `test_e2e_exam_center_gate.py` |

**À ajouter** : I10, un test qui parcourt **toutes** les routes `GET` accessibles aux rôles `candidate` et `center` pendant une tentative active, et qui échoue si une clé `correct_answer`, `correct_option_ids` ou `explanation` apparaît dans le JSON.

## 2. Tests par évolution

### Règles versionnées (1.1)
- La tentative fige `rule_set_id` ; changer la règle active ne modifie pas une tentative en cours ni une tentative notée.
- Le jeu `LEGACY-PROVISOIRE` reproduit exactement les résultats actuels (test de non-régression sur un échantillon de réponses).
- Une règle non approuvée ne peut pas être activée ; l'approbation par son auteur est refusée (quatre yeux).
- La migration est réversible : test `upgrade → downgrade → upgrade` sur PostgreSQL.

### Publication contrôlée (1.2)
- En mode `delayed`, ni le candidat ni l'agent ne voient le score avant `published_at` ; l'administrateur le voit.
- Aucune notification n'est émise avant la publication ; l'outbox réessaie après un échec.
- L'annulation d'un résultat publié est journalisée, avec motif.

### Banque (1.3, 1.4, 2.1)
- Démarrage refusé si `pool < question_count × min_pool_multiplier` (code `OFFICIAL_QUESTION_BANK_NOT_READY`).
- Personnalisation : sur 1 000 tirages simulés avec une banque ×5, recouvrement moyen entre deux examens < seuil fixé ; répartition par thème toujours exacte.
- En production, refus d'une banque dont l'empreinte correspond à la banque de démo.
- La révision vue par le candidat est celle de la correction, même après une modification de la question.

### Multi-réponses (2.2, 2.3)
- Tests de propriétés (Hypothesis) : juste ⇔ ensembles égaux ; l'ordre des choix est indifférent ; réponse vide = fausse ; option inconnue rejetée (422).
- Compatibilité : une réponse historique en chaîne est notée comme avant.
- Playwright : une question multi-réponses n'est validable qu'avec au moins une case cochée ; la consigne est affichée.

### Reprise et incidents (1.5, 1.6)
- Worker : une tentative échue depuis plus de N s est finalisée une seule fois, même si le worker tourne deux fois ou en concurrence avec le client.
- Suspension : le temps restant est gelé ; la reprise restitue le temps exact ; au-delà de `max_suspension_seconds`, un incident est créé ; seul un agent du centre peut suspendre (test 403).
- Playwright `exam-runtime-resilience` : coupure réseau à t+5 min puis à t−10 s ; aucune réponse synchronisée n'est perdue.

### Antifraude (4.1)
- Les événements du poste sont émis et rattachés à la tentative ; un candidat ne peut pas écrire sur la tentative d'un autre (IDOR).

### Sécurité des comptes (3.x)
- Admin sans 2FA : connexion refusée après la période de grâce.
- Jeton révoqué (déconnexion, changement de rôle) : 401.
- M6 : un compte dont l'e-mail correspond à celui d'un dossier sans `user_id` n'accède pas à ce dossier.

## 3. Campagnes hors CI

| Campagne | Quand | Critère de réussite |
|---|---|---|
| Répétition de bout en bout (`scripts/demo.sh check`) | Avant chaque démo ou pilote | Toutes les étapes vertes |
| Charge (k6/Locust) : pic national simulé | Avant le pilote | p95 < 500 ms sur `/answers`, 0 erreur 5xx |
| Coupure WAN réelle avec la passerelle edge | Pilote | 0 réponse perdue, rapprochement OK |
| Restauration PITR | Trimestrielle | RPO/RTO documentés et tenus |
| Revue de contenu de la banque (double relecture DNTT) | À chaque import | 100 % des questions relues par 2 personnes |
| Accessibilité (axe + lecteur d'écran) | Avant généralisation | 0 violation WCAG AA bloquante |

## 4. Exécution
```bash
scripts/demo.sh check                                          # répétition
docker run --rm -v "$PWD:/src:ro" coderoute-test:py312 …       # suite backend (voir CI)
cd frontend && npm run typecheck && npm run build && npx playwright test
```
PostgreSQL : les tests de migration et de verrou (`with_for_update`, verrous
consultatifs) doivent tourner sur PostgreSQL 16, pas seulement sur SQLite.
