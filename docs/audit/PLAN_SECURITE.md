# Plan de sécurité

> Périmètre : intégrité des examens et des résultats, confidentialité de la
> banque, données personnelles des candidats, disponibilité le jour de l'épreuve.

## 1. Actifs et menaces

| Actif | Menace principale | Impact |
|---|---|---|
| Banque officielle et clés de correction | Fuite (dépôt public, export, poste) | Examen compromis au niveau national |
| Résultats et attestations | Falsification, publication prématurée | Permis délivrés à tort |
| Comptes administrateurs et chefs de centre | Vol d'identifiants, jeton volé | Manipulation de résultats et de banque |
| Données candidats (identité, téléphone) | Fuite, usage non autorisé | Atteinte à la vie privée |
| Paiements | Double débit, fraude, détournement de remboursement | Financier |
| Disponibilité le jour J | Panne WAN, surcharge | Sessions annulées |

## 2. Mesures existantes (à préserver)
- Bonnes réponses jamais servies pendant l'épreuve ; résultat candidat sans correction.
- Trace hachée de chaque tentative ; audit HMAC chaîné avec ancre, et vérification exposée.
- Contrôles d'identité, de paiement, de check-in, de fenêtres et de poste avant le démarrage.
- Limitation des connexions, CSRF, bcrypt, validation des secrets de production, docs API désactivées en production.
- Webhooks de paiement signés ; idempotence de la création de paiement ; remboursements à quatre yeux.
- Edge : bail Ed25519, SQLite chiffré AES-256-GCM, releases signées et chaîne d'approvisionnement.
- Pseudonymisation des journaux SOC.

## 3. Plan d'action par criticité

### Critique
| ID | Mesure | Vérification |
|---|---|---|
| S1 | Sortir la banque officielle du dépôt ; import signé ; refus en production de la banque de démo | Test 1.4 ; `git grep` sans aucune clé officielle |
| S2 | Supprimer tout chemin qui crée des comptes à mot de passe connu en production ; README corrigé | Test du garde ; revue doc |
| S3 | Vérification humaine des `.env*` suivis ; retrait du suivi ; rotation de tout secret exposé ; scan de l'historique git (gitleaks) | Rapport gitleaks propre |
| S4 | Publication contrôlée des résultats | Tests 1.2 |

### Élevé
| ID | Mesure |
|---|---|
| S5 | 2FA obligatoire pour les rôles privilégiés |
| S6 | Jetons en cookie `HttpOnly`/`Secure`/`SameSite=Strict` ; refresh tournant ; révocation `jti`/`token_version` |
| S7 | Supprimer le rattachement candidat par e-mail (M6) ; test IDOR |
| S8 | CSP stricte, `frame-ancestors 'none'`, HSTS (nginx/Render) |
| S9 | Production en promotion manuelle ; protection de branche `main` (revue obligatoire, checks requis) |
| S10 | Approbation à quatre yeux des questions et des règles d'examen |

### Moyen
| ID | Mesure |
|---|---|
| S11 | Mode kiosque et événements de surveillance du poste |
| S12 | Rendre les échecs d'initialisation (`create_all`) bloquants ; plus de `except Exception` silencieux sur les chemins critiques |
| S13 | Signature des résultats intégrée au QR de l'attestation |
| S14 | Durées de conservation et purge automatique (après décision R18) |
| S15 | Journaliser tout export de données nominatives (qui, quoi, quand) |

## 4. Données personnelles
- Inventaire : identité, numéro de pièce, téléphone, e-mail, photo éventuelle, résultats, paiements.
- **À confirmer juridiquement** (R18) : texte guinéen applicable à la protection des données personnelles, autorité compétente, exigences de localisation de l'hébergement, durées de conservation. Le présent dossier ne présume d'aucune de ces réponses.
- Minimisation : ne pas envoyer le score par WhatsApp ou SMS sans base légale et consentement validés.

## 5. Gestion des secrets
- Secrets uniquement dans le gestionnaire du fournisseur, jamais dans git ; seuls `*.example` et `*.template` sont suivis.
- Rotation : `SECRET_KEY`, `CSRF_SECRET`, `AUDIT_CHAIN_HMAC_KEY` (avec une nouvelle ancre), clés Mobile Money, clés edge. La procédure est déjà décrite dans `SECURITY_ROTATION.md` et doit être testée une fois.

## 6. Réponse à incident
| Événement | Action immédiate |
|---|---|
| Fuite de la banque | Gel des sessions, retrait des questions exposées, import d'une banque de secours |
| Chaîne d'audit rompue | Gel des publications, investigation `broken_at_seq`, restauration PITR si nécessaire |
| Compte privilégié compromis | Désactivation, révocation des jetons (S6), revue de l'audit sur la période |
| Panne WAN le jour J | Bascule edge ; sinon suspension (1.6) et report |

## 7. Revues
- Revue de sécurité à chaque PR qui touche l'authentification, l'examen, les résultats, la banque ou les paiements (skill `security-review`, voir `AGENTS_AND_SKILLS.md`).
- Test d'intrusion externe avant le pilote, et avant la généralisation.
