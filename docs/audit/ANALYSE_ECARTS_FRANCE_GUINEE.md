# Analyse des écarts France ↔ CodeRoute Guinée

> **Avertissement** : le dispositif français sert ici de **référence de bonnes
> pratiques**, pas de réglementation applicable. Aucune règle guinéenne n'est
> supposée. Les valeurs actuelles de CodeRoute sont des **paramètres
> opérationnels provisoires**, comme le code le dit lui-même (`exam_engine.py:11-12`,
> `session_rules.py:11-12`).
>
> Complète `docs/BONNES_PRATIQUES_INTERNATIONALES.md` (France ETG, Royaume-Uni DVSA).

## 1. Principes de référence demandés

| Principe (référence France) | CodeRoute aujourd'hui | Écart | Priorité |
|---|---|---|---|
| Questions illustrées par photos et vidéos de situations réelles | Contrat média complet, mais 0 question officielle illustrée et des médias de démo tronqués | **Contenu** | P0 |
| QCM à une ou plusieurs bonnes réponses | Réponse unique, sous forme de texte | **Modèle de données + notation** | P0 |
| Chronomètre visible | Chrono serveur synchronisé, affiché | — | — |
| Progression visible | n / 40 | — | — |
| Examen personnalisé tiré d'une large banque | Pool = 40 questions : examen identique pour tous | **Contenu + règle de tirage** | P0 |
| Conditions d'examen sécurisées | Contrôle d'identité, fenêtres horaires, postes enregistrés, trace, audit ; pas de détection sur le poste, pas de mode kiosque imposé | Partiel | P1 |
| Familiarisation avec l'interface | Examen blanc et entraînement ; pas de tutoriel guidé avant l'épreuve | Faible | P2 |
| Correction automatique | Oui | — | — |
| Publication contrôlée des résultats | Immédiate, avec notification | **Processus** | P0 |
| Pas de communication des bonnes réponses | Respecté côté candidat depuis la PR #254 ; banque publique sur GitHub | **Confidentialité** | P0 |

## 2. Écarts techniques détaillés

### 2.1 Questions à réponses multiples
- **France** : 1 à 4 propositions, une ou plusieurs bonnes ; la question est juste seulement si la combinaison est exacte.
- **CodeRoute** : `Question.correct_answer: str` ; le candidat envoie le **texte** de l'option.
- **Cible** : identifiants d'options stables (`A`…`D`), `correct_options: list[str]`, notation par égalité d'ensembles, réponse candidate de type `list[str]`. Compatibilité : une question à une seule réponse devient une liste d'un élément (voir `ARCHITECTURE_CIBLE.md` §3).

### 2.2 Taille et personnalisation de la banque
- **France** : banque nationale de plusieurs centaines à milliers de questions, renouvelée, confidentielle.
- **CodeRoute** : 40 questions officielles, dont la clé est publique.
- **Cible** : banque **hors dépôt**, importée par la DNTT, versionnée. Le démarrage d'un examen refuse un pool inférieur à un multiple **paramétrable** de la répartition (ex. ×5). Ce garde existe déjà pour un pool inférieur à 40 (`_require_official_bank_ready`) ; il suffit de rendre le seuil configurable.

### 2.3 Publication des résultats
- **France** : résultat différé, consultable en ligne ; relevé des fautes par thème, sans les bonnes réponses.
- **CodeRoute** : fautes par thème ✅ ; publication immédiate ❌.
- **Cible** : statut `scored` → `published`, avec un délai paramétrable, ou une validation du PV de session par le chef de centre, ou les deux. Notifications envoyées seulement à la publication.

### 2.4 Incident pendant l'épreuve
- **France** : l'incident technique est géré par l'opérateur ; le candidat ne doit pas être pénalisé.
- **CodeRoute** : le chrono n'est jamais suspendu ; le rattrapage tire de nouvelles questions.
- **Cible** : **suspension** journalisée (incident → pause → reprise par l'agent) et temps restant calculé sur la durée active, avec une durée de suspension maximale paramétrable.

### 2.5 Conditions de passage
| Élément | France (référence) | CodeRoute | Décision |
|---|---|---|---|
| Nombre de questions / seuil / durée | 40 q, ≥ 35, ~30 min | 40 / 35 / 30 min | **DNTT** |
| Temps par question imposé | Oui (environ 20 s, vidéo comprise) | Non : temps global | **DNTT** |
| Retour arrière | Non (question par question) | Non (séquentiel) | **DNTT** |
| Validité du code | 5 ans / 5 tentatives à l'épreuve pratique | Aucune | **DNTT** |
| Délai avant nouvelle tentative | Variable selon l'opérateur | Aucun | **DNTT** |
| Contrôle d'identité | Pièce d'identité + photo | Pièce validée en amont + code de convocation | **DNTT** (photo le jour J ?) |

## 3. Ce que CodeRoute fait déjà mieux ou de façon équivalente
- Trace cryptographique de chaque tentative et **journal d'audit HMAC chaîné** vérifiable (plus que le minimum observé en France).
- **Continuité hors-ligne** des centres (passerelle edge) : adaptée au contexte réseau guinéen.
- Détection statistique d'anomalies par centre, séparation des tâches sur les remboursements.
- Paiement Mobile Money intégré au parcours.

## 4. Décisions réglementaires à obtenir de la DNTT

Aucune de ces valeurs ne doit être codée comme « norme guinéenne » sans un acte
de référence (arrêté, décision, note de service) archivé avec sa date d'effet.

| # | Question à trancher | Valeur provisoire actuelle |
|---|---|---|
| R1 | Nombre de questions par épreuve | 40 |
| R2 | Seuil d'admission | 35 |
| R3 | Durée totale, ou temps par question | 30 min globales |
| R4 | Répartition par thème et liste officielle des thèmes | 8 thèmes (10/6/5/5/4/4/3/3) |
| R5 | Questions à réponses multiples autorisées ? | Non |
| R6 | Questions éliminatoires ou pondérées ? | Non |
| R7 | Taille minimale de la banque et rythme de renouvellement | — |
| R8 | Langues de l'épreuve (écrit / audio) et validation des traductions | Écrit en français, audio prévu |
| R9 | Délai et mode de publication des résultats | Immédiat |
| R10 | Contenu communiqué au candidat (score, fautes par thème) | Score + thèmes |
| R11 | Procédure et délai de recours | Recours libre |
| R12 | Durée de validité de la réussite | Illimitée |
| R13 | Délai et nombre maximal de nouvelles tentatives | Aucun |
| R14 | Clôture des inscriptions avant la session | Aucune |
| R15 | Jours et horaires autorisés des sessions | Aucune contrainte |
| R16 | Capacité maximale par session et sessions par semaine | 35 / 3 |
| R17 | Gestion des incidents (pause, rattrapage, délai) | Rattrapage uniquement |
| R18 | Hébergement et conservation des données personnelles (lieu, durées), autorité de contrôle compétente | Francfort ; durées non fixées |
| R19 | Aménagements pour les candidats en situation de handicap ou non lecteurs (temps majoré, audio) | — |
| R20 | Tarifs officiels et modalités de remboursement | Paramétrés dans `tarifs.py` |
