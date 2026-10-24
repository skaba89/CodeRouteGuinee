# Bonnes pratiques internationales — examen théorique du permis

Comparaison de CodeRoute Guinée avec les dispositifs de référence, d'abord
l'épreuve théorique générale (ETG) française et le *theory test* britannique
(DVSA). État au 24 octobre 2026.

Les pratiques citées viennent des textes et sources listés en fin de document.
Les sources secondaires (presse spécialisée, auto-écoles) sont signalées comme
telles. Avant toute décision réglementaire, vérifier les textes officiels
(Légifrance, gov.uk).

## 1. Ce que font les références

| Pratique | France (ETG) | Royaume-Uni (DVSA) |
|---|---|---|
| Format | 40 questions, 35 bonnes réponses requises, certaines en vidéo | 50 questions (43 requises) + 14 clips de perception des risques |
| Communication du résultat | Différée de 24 h depuis l'arrêté du 29/04/2024 ; score et **fautes par thème**, sans les bonnes réponses | Au centre, juste après l'épreuve. En cas d'échec, une lettre indique les parties insuffisantes, **sans les bonnes réponses** |
| Délai avant de repasser | Pas de délai minimal | Au moins 3 jours ouvrables |
| Inscription | Close au plus tard **la veille** de la session (arrêté du 16/04/2026) | — |
| Plages horaires | Pas de session le dimanche ni les jours fériés ; entre 8 h et 20 h (arrêté de 2024) | — |
| Contrôle d'identité | À l'entrée **et pendant** l'épreuve, vidéosurveillance en cas de suspicion (2026) | Permis de conduire à photo (photocard) obligatoire ; sans document valide, l'épreuve est annulée sans remboursement |
| Surveillance des centres | Indicateurs suivis en temps réel : taux de réussite, éloignement géographique des candidats, dépassement des créneaux. Contrôles renforcés systématiques des centres atypiques. 83 centres fermés en 2024 | — |
| Encadrement des opérateurs | Contrôle interne obligatoire, référent anti-fraude régional, plan de contrôle annuel des centres, autorisation préfectorale des sites pour 5 ans | — |
| Validité | Code valable 5 ans | Certificat valable 2 ans |

## 2. Alignements réalisés dans CodeRoute

| Pratique | Mise en œuvre | Où |
|---|---|---|
| **Confidentialité des réponses officielles** | Après l'examen officiel, le candidat et l'agent de centre reçoivent le score et les fautes par thème. La correction détaillée est réservée à l'administration, pour les recours. | `GET /exams/{id}/results` (`detail_level`, `themes`) |
| **Banque officielle non exposée** | Le mode entraînement ne sert que la banque d'entraînement (160 questions) et n'expose plus les questions officielles avec leurs réponses. La liste des questions est réservée à l'autorité de la banque : elle n'est plus ouverte aux agents de centre. | `routers/training.py`, `GET /questions` |
| **Surveillance statistique des centres** | Taux de réussite anormal (test binomial, z ≥ 3, à partir de 20 examens), plus de 50 % de candidats venant d'une autre région, examens démarrés hors créneau. Un centre signalé appelle un contrôle sur place : c'est un indicateur, pas une preuve. | `app/center_anomalies.py`, `GET /dashboard/center-anomalies`, encart du portail ministériel |
| **Vérification publique des attestations** | QR code imprimé sur l'attestation, qui renvoie vers une page publique de vérification. Chaque vérification est journalisée, et le numéro de pièce d'identité n'est pas exposé. | `pdf_service.py`, `#/verifier/<id>`, `PUBLIC_APP_URL` |
| **Séparation des tâches (finances)** | L'auteur d'une demande de remboursement ne peut pas la décider (contrôle à « quatre yeux »), quel que soit son rôle. | `routers/payment_refunds.py` |
| Contrôle d'entrée | Déjà en place : identité vérifiée, paiement confirmé, bon centre, fenêtre horaire, poste enregistré, chaque refus journalisé. | `exam_center_gate.py`, `routers/entries.py` |
| Journal infalsifiable | Déjà en place : chaîne HMAC. Corrigée pour couvrir aussi les écritures faites hors de l'API. | `audit_chain.py` |

## 3. Décisions qui reviennent à la DNTT

Ces points relèvent de la réglementation guinéenne. Le code ne les impose pas
encore, car un choix technique ne doit pas trancher une question juridique.

1. **Banque officielle confidentielle et suffisamment large.** C'est le point le plus important.
   - Aujourd'hui, le pool de l'examen officiel se limite aux 40 questions de démonstration de `QUESTIONS_GN` : tous les examens sont donc identiques.
   - Ces 40 questions figurent dans un dépôt GitHub **public**, et 5 d'entre elles sont aussi dans le bundle frontend.
   - La banque réelle doit être importée par `/questions/import-official` depuis un support maîtrisé par la DNTT, jamais versionnée, et compter plusieurs centaines de questions.
2. **Communication différée du résultat**, par exemple 24 h comme en France. Ce délai casse l'intérêt d'une triche organisée sur place.
3. **Clôture des inscriptions la veille de la session**, pour laisser le temps de contrôler la liste des candidats attendus.
4. **Plages horaires autorisées** (jours et heures).
5. **Durée de validité** de la réussite à l'examen théorique (5 ans en France, 2 ans au Royaume-Uni) et **délai minimal avant de repasser**.
6. **Questions vidéo et perception des risques**, sur le modèle des 14 clips du DVSA. Cela suppose une production de médias homologués : voir `docs/MEDIA_FACTORY_GUINEE.md`.
7. **Questions à réponses multiples**, où toutes les propositions exactes doivent être cochées. Le moteur actuel ne gère qu'une seule bonne réponse par question.
8. **Organisation anti-fraude**, sur le modèle français : référent anti-fraude, plan de contrôle annuel des centres, durée d'agrément des centres, sanctions (interdiction de repasser l'examen).
9. **Seuils de surveillance**, à homologuer : volume minimal, z-score, part de candidats éloignés.

## Sources

- [Question écrite au Sénat n° 00953 (2024) et réponse du ministère de l'Intérieur (5 juin 2025)](https://www.senat.fr/questions/base/2024/qSEQ241000953.html) — mesures de l'arrêté du 29 avril 2024, chiffres 2024.
- [Digischool — Examen du code de la route au 1er juillet 2026](https://www.digischool.fr/articles/auto/actualites/examen-code-de-la-route-1er-juillet-2026/) — arrêté du 16 avril 2026 (source secondaire ; texte officiel : Légifrance JORFTEXT000053974673).
- [Le Repaire des Motards — renforcement de la lutte contre la fraude](https://www.lerepairedesmotards.com/actualites/2026/renforcement-lutte-contre-fraude-examen-code-route.php) — autorisation préfectorale, contrôles renforcés (source secondaire).
- [Ornikar — résultat du code de la route](https://www.ornikar.com/code/examen/apres/resultat-code) — contenu du résultat, fautes par thème, validité de 5 ans (source secondaire).
- [En Voiture Simone — fraude à l'examen du code](https://www.envoituresimone.com/code-de-la-route/guides/fraude) (source secondaire).
- [gov.uk — Theory test: pass mark and result](https://www.gov.uk/theory-test/pass-mark-and-result) et [gov.uk — What to take](https://www.gov.uk/theory-test/what-to-take) — résultat, validité, délai de repassage, pièces exigées.
- [nidirect — Taking the theory test](https://nidirect.gov.uk/node/16613) et [Driving Theory 4 All — pass mark](https://www.drivingtheory4all.co.uk/theory-test-pass-mark) — format du *theory test* britannique.
