# Feuille de route priorisée

> Priorités : **P0** = bloquant pour un examen officiel · **P1** = nécessaire au
> pilote · **P2** = généralisation. Chaque lot = une PR, avec tests, sans fusion
> automatique dans `main`. Les estimations sont en jours de développement pour une
> personne, hors délais de décision DNTT.

## Lot 0 — Hygiène immédiate (sans changement métier) · 1 à 2 j

| # | Action | Risque traité | Type |
|---|---|---|---|
| 0.1 | Vérification par un humain des `.env*` suivis ; retrait du suivi git et rotation si nécessaire | E1 | Sécurité |
| 0.2 | README : retirer l'étape `seed_full` en production, corriger les chiffres, isoler les comptes de démo dans `DEMO.md` | C5, README | Doc |
| 0.3 | Garde : `seed_full` et `seed_demo_dntt` refusent `ENVIRONMENT=production` **sans exception possible** (+ test) | C5 | Code |
| 0.4 | URL du certificat via `public_app_url` (+ test) | M4 | Code |
| 0.5 | `GET /questions` refusé pour `expired` (+ test) | M5 | Code |
| 0.6 | Remplacer les 4 médias tronqués | M7 | Contenu |

## Lot 1 — P0 Intégrité de l'examen · 10 à 15 j

| # | Action | Dépend de |
|---|---|---|
| 1.1 | `exam_rule_sets` versionnés + rattachement des tentatives (jeu `LEGACY-PROVISOIRE`, aucun changement de comportement) | — |
| 1.2 | Publication contrôlée des résultats (`scored → published`, outbox de notifications) ; mode `immediate` par défaut tant que R9 n'est pas tranchée | 1.1, R9 |
| 1.3 | Taille minimale de la banque paramétrable (`min_pool_multiplier`) | 1.1, R7 |
| 1.4 | Banque officielle **hors dépôt** : import signé ; `QUESTIONS_GN` réservé à la démo et à l'entraînement ; refus en production d'une banque dont l'empreinte correspond à la banque de démo publique | — |
| 1.5 | Finalisation serveur des tentatives échues (worker idempotent) | — |
| 1.6 | Suspension et reprise sur incident (`active_seconds`) | R17 |

## Lot 2 — P0/P1 Banque multimédia et multi-réponses · 10 à 15 j

| # | Action | Dépend de |
|---|---|---|
| 2.1 | `question_revisions` immuables + trace `(question_id, revision_id)` | — |
| 2.2 | Identifiants d'options + `correct_option_ids` + notation par ensembles (format historique toujours accepté) | 2.1, R5 |
| 2.3 | UI candidat : cases à cocher multi-réponses, consigne explicite | 2.2 |
| 2.4 | Approbation à quatre yeux des révisions | 2.1 |
| 2.5 | Préchargement et vérification des médias avant la session | — |
| 2.6 | Production de contenu : **banque DNTT** (cible ≥ 5 × 40, illustrée) et audio en langues nationales | DNTT |

## Lot 3 — P1 Sécurité des comptes · 4 à 6 j

| # | Action |
|---|---|
| 3.1 | 2FA obligatoire pour `admin`, `super_admin`, chef de centre |
| 3.2 | Jetons en cookie `HttpOnly` ; refresh tournant ; révocation `jti` / `token_version` |
| 3.3 | Suppression du rattachement candidat par e-mail (après vérification de M6) + test IDOR |
| 3.4 | En-têtes CSP stricts sur le frontend |

## Lot 4 — P1 Conditions d'examen et antifraude · 6 à 8 j

| # | Action |
|---|---|
| 4.1 | Émission des événements de surveillance par le poste (focus, plein écran, réseau) |
| 4.2 | Mode kiosque : profil navigateur verrouillé ou application edge |
| 4.3 | Check-list d'ouverture de session obligatoire |
| 4.4 | PV de session signé |
| 4.5 | Tutoriel de familiarisation (3 questions d'essai) avant l'épreuve officielle |

## Lot 5 — P1 Exploitation · 5 à 8 j

| # | Action |
|---|---|
| 5.1 | Préproduction distincte ; production en promotion manuelle (plus d'`autoDeploy` sur `main`) |
| 5.2 | Exercice de restauration (PITR) chronométré et documenté |
| 5.3 | Essai terrain de la passerelle edge (coupure WAN réelle pendant une session pilote) |
| 5.4 | Tests de charge sur un pic de session nationale |

## Lot 6 — P2 Généralisation

Accessibilité WCAG AA et aménagements · statistiques par question · reporting
matérialisé · tests unitaires frontend (Vitest) · résorption de la réécriture des
routes · documentation : désigner une source de vérité et archiver le reste de `docs/`.

## Chemin critique

```text
Décisions DNTT (R1-R20) ──► 1.1 règles ──► 1.2 publication / 1.3 banque min.
Banque DNTT (contenu)   ──► 1.4 import ──► 2.1 révisions ──► 2.2/2.3 multi-réponses
                                                         └─► Pilote 1 centre (Lots 3-5)
```

Le contenu (banque officielle illustrée) et les décisions réglementaires sont les
facteurs limitants, pas le code.
