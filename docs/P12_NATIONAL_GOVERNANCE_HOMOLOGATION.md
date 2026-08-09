# P12 — Gouvernance nationale et homologation DNTT

## 1. Objet

P12 transforme les paramètres d'examen et les preuves d'exploitation de CodeRoute Guinée en un **dossier institutionnel versionné et contrôlable**.

Cette phase ne modifie pas silencieusement le moteur de notation. Elle ajoute une couche de gouvernance entre :

1. la règle institutionnelle proposée ;
2. sa base juridique ou décisionnelle ;
3. sa validation par plusieurs acteurs ;
4. l'implémentation technique ;
5. la preuve que l'infrastructure est exploitable ;
6. la décision finale d'homologation.

P12 est conçu pour empêcher qu'une constante de code devienne, par simple usage, une « règle officielle » non validée.

---

## 2. Point juridique et institutionnel essentiel

Le moteur utilise actuellement le contrat technique suivant pour l'examen théorique Catégorie B :

- 40 questions ;
- seuil technique : 35 réponses correctes ;
- durée technique : 30 minutes ;
- distribution catégorielle définie dans `backend/app/exam_engine.py` ;
- un passage par session.

**Ces valeurs sont des paramètres techniques courants. P12 ne les qualifie pas de règle juridique ou réglementaire officielle.**

Elles ne doivent être présentées comme règles DNTT homologuées qu'après rattachement d'une référence institutionnelle valable et validation humaine dans le workflow P12.

Si la DNTT retient par exemple 40/36/25 minutes, P12 permet d'approuver ce document, mais refuse son activation tant que le runtime continue d'exécuter 40/35/30. Le changement de moteur doit être développé, testé et déployé séparément, puis la politique peut être activée.

---

## 3. Principe : aucune bascule réglementaire silencieuse

Cycle normal :

```text
DNTT rédige / transmet la règle
          │
          ▼
Draft P12 versionné
          │
          ▼
Soumission
          │
          ▼
Deux approbateurs distincts
          │
          ▼
APPROVED
          │
          ├── runtime différent ──> BLOQUÉ
          │
          └── runtime aligné ─────> activation super_admin
                                      │
                                      ▼
                                    ACTIVE
```

Une politique peut donc être juridiquement approuvée avant que le logiciel ne soit prêt, sans que le système applique une règle qu'il ne sait pas encore exécuter.

---

## 4. Stockage institutionnel

P12 réutilise `InstitutionalAuthorization` pour éviter une migration de schéma pendant cette phase.

Chaque politique ou dossier possède :

- une référence institutionnelle unique ;
- un statut ;
- un document JSON canonique dans `scope` ;
- une empreinte SHA-256 `document_sha256` ;
- les dates d'effet ;
- les acteurs du workflow dans le document ;
- des événements `AuditLog` à chaque étape.

Une modification directe du JSON sans recalcul via le workflow est détectée par `INSTITUTIONAL_DOCUMENT_HASH_MISMATCH`.

L'empreinte P12 protège l'intégrité logique du document. Pour une signature juridiquement qualifiée, une PKI gouvernementale, une signature électronique qualifiée ou un HSM devra être ajouté dans une phase ultérieure.

---

## 5. Politique nationale d'examen

Type de document :

```text
coderoute_national_exam_policy_v1
```

Référence :

```text
DNTT-POLICY-<CODE>-<VERSION>
```

Exemple :

```text
DNTT-POLICY-OFFICIAL_EXAM_CATEGORY_B-2026.1
```

Le document contient notamment :

- code ;
- version ;
- paramètres d'examen ;
- distribution par catégorie ;
- règle d'unicité de passage ;
- éventuel cooldown de nouvelle tentative ;
- références juridiques / décisions DNTT ;
- rationale ;
- rédacteur ;
- date de soumission ;
- approbations ;
- activation ;
- politique remplacée ;
- hash du document.

---

## 6. Références juridiques et décisionnelles

Une politique ne peut pas être créée sans au moins une `legal_reference`.

Le champ peut représenter selon le dispositif réellement retenu :

- loi ;
- décret ;
- arrêté ;
- décision DNTT ;
- procès-verbal de commission ;
- note d'homologation ;
- document officiel signé ;
- autre référence administrative reconnue.

P12 stocke la référence fournie ; il **ne détermine pas lui-même la valeur juridique du document**.

Avant déploiement national, la DNTT et le service juridique doivent confirmer quelles références font autorité.

---

## 7. Séparation des tâches — règle des quatre yeux

Le workflow impose :

- le rédacteur ne peut pas approuver sa propre politique ;
- un approbateur ne peut signer qu'une fois ;
- deux acteurs distincts doivent approuver ;
- seul `super_admin` peut activer ;
- une activation est auditée.

Ainsi, un seul compte ne peut pas rédiger puis auto-valider une règle nationale.

Pour le dossier d'homologation :

- le créateur du dossier ne peut pas l'approuver ;
- deux approbateurs distincts sont requis ;
- la décision finale est réservée à `super_admin` ;
- la readiness est recalculée au moment de la décision.

---

## 8. Politique unique tant que le moteur est mono-contrat

Le moteur actuel applique un seul contrat officiel global Catégorie B.

P12 refuse donc l'activation simultanée d'un autre code national :

```text
ACTIVE_POLICY_CODE_CONFLICT
```

Cette restriction évite de faire croire que des politiques Catégorie A, C ou D sont supportées alors que le moteur n'a pas encore un routage explicite par catégorie.

Elle sera retirée uniquement lors d'une évolution multi-politique où :

- chaque tentative porte une catégorie de permis ;
- chaque catégorie résout sa politique active ;
- les traces d'examen enregistrent le policy id/version/hash ;
- la notation utilise le contrat associé à la tentative.

---

## 9. Contrat technique et contrôle de dérive

Endpoint :

```text
GET /api/v1/national-governance/technical-contract
```

Il expose :

- contrat réellement compilé dans le moteur ;
- politique active ;
- différences éventuelles.

Champs actuellement comparés :

- question_count ;
- pass_threshold ;
- duration_minutes ;
- category_distribution ;
- one_attempt_per_session.

Une activation avec dérive retourne :

```text
TECHNICAL_CONFIGURATION_MISMATCH
```

Le `retake_cooldown_hours` est un paramètre de politique P12 mais n'est pas encore une constante du moteur historique ; il n'est donc pas utilisé pour prétendre à un alignement technique tant qu'une implémentation dédiée n'existe pas.

---

## 10. Readiness nationale P12

Endpoint :

```text
GET /api/v1/national-governance/readiness
```

P12 ne remplace pas les readines techniques précédentes. Il construit une **porte d'homologation** sur des preuves déjà présentes.

Contrôles bloquants actuels :

1. politique nationale active ;
2. alignement politique/runtime ;
3. banque de questions officielle suffisante ;
4. répartition catégorielle suffisante ;
5. au moins un centre actif/accrédité ;
6. preuve de backup hors région récente (<= 26 h) ;
7. restore drill récent (<= 35 jours) ;
8. preuve de failover API récente (<= 35 jours).

Le résultat contient :

```json
{
  "go_live_allowed": false,
  "blockers": ["active_policy", "restore_drill"]
}
```

`go_live_allowed=true` signifie uniquement que les contrôles automatisables P12 sont satisfaits. Cela **ne constitue pas à lui seul une homologation gouvernementale**.

---

## 11. Banque officielle de questions

Le check P12 :

- prend uniquement les questions `is_active=true` et `validation_status=approved` ;
- applique le filtre qui exclut le dataset historique d'entraînement ;
- vérifie le nombre total ;
- vérifie chaque catégorie exigée par la politique.

Une banque de 40 questions n'est donc pas suffisante si, par exemple, la politique demande 10 questions de signalisation mais que la banque n'en contient que 5 éligibles.

---

## 12. Dossier d'homologation

Type :

```text
coderoute_national_homologation_dossier_v1
```

Référence :

```text
DNTT-HOMO-...
```

Le dossier enregistre :

- politique active référencée ;
- SHA-256 de cette politique ;
- portée `pilot` ou `national` ;
- preuves institutionnelles ;
- snapshot de readiness lors de la soumission ;
- approbations ;
- décision finale ;
- nouveau snapshot de readiness lors de la décision.

La politique ne peut donc pas être remplacée entre la préparation et la décision sans être détectée.

---

## 13. Cinq pièces institutionnelles obligatoires

Avant soumission du dossier :

1. `dntt_exam_rules`
   - validation formelle des règles d'examen ;
2. `legal_review`
   - revue juridique et base réglementaire ;
3. `security_assessment`
   - audit sécurité / ANSSI ou autorité compétente selon procédure retenue ;
4. `operations_readiness`
   - recette exploitation, astreinte, PRA/PCA, supervision ;
5. `content_signoff`
   - validation officielle de la banque de questions et médias.

Le code refuse le dossier avec :

```text
HOMOLOGATION_EVIDENCE_MISSING
```

si une pièce manque.

P12 stocke la référence et la date de la preuve, pas le document confidentiel lui-même. Les pièces sources doivent être conservées dans une GED institutionnelle avec ses propres contrôles d'accès et de conservation.

---

## 14. Décision finale

Avant `homologated`, le serveur recontrôle :

- dossier prêt à décision ;
- deux approbations ;
- politique toujours active ;
- référence de politique identique ;
- hash de politique identique ;
- readiness nationale recalculée ;
- aucun blocker.

Une ancienne capture d'écran « tout vert » ne suffit donc pas à homologuer plus tard un système dont les preuves sont devenues obsolètes.

---

## 15. Interface DNTT

Le `NationalDashboard` reçoit une carte :

```text
Homologation nationale — DNTT
```

Elle affiche :

- politique active et version ;
- contrat technique réel ;
- alignement ;
- checks de readiness ;
- blockers ;
- versions de politiques ;
- approbations ;
- hash des documents ;
- dossiers d'homologation ;
- nombre de pièces rattachées.

Les boutons visibles n'ont jamais autorité seuls : RBAC, séparation des tâches, statuts et contrôles sont exécutés de nouveau côté backend.

---

## 16. Procédure recommandée de première homologation

### Étape A — confirmer les règles DNTT

Réunir la DNTT, juridique, contenu et équipe projet.

Documenter explicitement :

- catégories de permis couvertes ;
- nombre de questions ;
- seuil ;
- durée ;
- catégories et pondérations ;
- règles d'absence de réponse ;
- nouvelle tentative ;
- accessibilité / audio ;
- langues ;
- fenêtres centre ;
- conditions d'annulation ;
- traitement fraude et recours.

### Étape B — créer la politique

Depuis le dashboard ou l'API, créer le draft avec la référence officielle.

### Étape C — double approbation

Faire intervenir deux comptes institutionnels distincts du rédacteur.

### Étape D — contrôler l'alignement

Vérifier :

```text
GET /api/v1/national-governance/technical-contract
```

Si drift : ne pas activer. Corriger le logiciel via une PR, tests, déploiement et recette.

### Étape E — activer la politique

Activation par `super_admin` seulement après alignement.

### Étape F — réaliser les preuves d'exploitation

Clore les preuves P10/P10.2 :

- backup hors région ;
- restore ;
- failover ;
- PITR fournisseur ;
- supervision ;
- sécurité.

### Étape G — ouvrir le dossier

Créer le dossier d'homologation lié à la politique active.

### Étape H — rattacher les cinq pièces

Chaque preuve doit avoir une référence documentaire institutionnelle retrouvable.

### Étape I — soumettre / approuver / décider

Le système refait tous les contrôles avant la décision finale.

---

## 17. Révocation et évolution d'une règle

Une politique active peut être révoquée par `super_admin` avec motif.

Pour une évolution :

1. créer une nouvelle version ;
2. garder l'ancienne active pendant la revue ;
3. obtenir deux approbations ;
4. adapter le runtime si nécessaire ;
5. vérifier l'alignement ;
6. activer la nouvelle version ;
7. l'ancienne version du même code devient `superseded`.

Ne jamais modifier en place une politique active.

---

## 18. Tests P12

Backend :

- contrat actuel explicitement aligné ;
- rédacteur ne peut auto-approuver ;
- deux approbateurs distincts ;
- activation après quatre yeux ;
- règle différente du runtime bloquée ;
- modification directe du document détectée ;
- second code de politique actif bloqué ;
- dossier sans les cinq pièces bloqué.

Frontend E2E :

- aucune politique active => `Go-live bloqué` ;
- politique active + checks verts => `Éligible au dossier` ;
- paramètres techniques visibles ;
- référence DNTT visible.

Workflow :

```text
.github/workflows/p12-governance-pr-ci.yml
```

---

## 19. Critères de passage P12

Le code P12 peut être fusionné lorsque :

- CI backend P12 est verte et observable ;
- typecheck/build frontend sont verts ;
- E2E P12 est vert ;
- diff P12 ne modifie pas le moteur d'examen ;
- aucune valeur 40/35/30 n'est décrite comme homologuée sans preuve DNTT ;
- le workflow quatre yeux est validé ;
- la mutation directe de document est détectée.

Le **passage en homologation réelle** demande en plus :

- référence officielle fournie par DNTT/juridique ;
- approbateurs institutionnels nominativement habilités ;
- pièces sources dans la GED ;
- issue P10.2 go-live / preuves PRA traitée ;
- sécurité P11 activée et recettée si requise dans le dispositif homologué ;
- décision humaine finale.

---

## 20. Limites restantes

P12 ne fournit pas encore :

- signature électronique qualifiée ;
- PKI gouvernementale ;
- HSM de signature des décisions ;
- GED réglementaire ;
- parapheur électronique ;
- gestion d'une politique différente par catégorie A/B/C/D ;
- publication automatique d'un arrêté ou décret ;
- détermination juridique de la règle 40/35/30 ;
- homologation automatique par l'État.

Ces éléments appartiennent au prochain niveau d'industrialisation institutionnelle.

---

## 21. Principe de présentation au gouvernement

La formulation recommandée est :

> « CodeRoute Guinée dispose d'un moteur actuellement configuré avec 40 questions, un seuil technique de 35 réponses correctes et 30 minutes. P12 permet à la DNTT de versionner, référencer, faire approuver et homologuer formellement ces paramètres — ou toute autre règle retenue — sans qu'une modification réglementaire puisse s'appliquer silencieusement au moteur. »

Cette formulation distingue clairement la capacité technique de la décision réglementaire.
