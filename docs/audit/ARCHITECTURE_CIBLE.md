# Architecture cible — CodeRoute Guinée

> Principe directeur : **évolution, pas reconstruction**. On garde FastAPI,
> SQLAlchemy 2, Alembic, PostgreSQL 16, React 19/Vite, la passerelle edge,
> l'audit chaîné et les gardes existants. Chaque évolution passe par une
> migration additive, réversible et testée, avec une période de compatibilité.

## 1. Vue d'ensemble

```text
                 ┌──────────────────────── Plateforme centrale ───────────────────────┐
 Candidat ──HTTPS─┤ Front React (PWA)  ──►  API FastAPI                              │
 Auto-école       │                         ├─ Domaine Examen  (règles versionnées) │
 Admin / DNTT     │                         ├─ Banque (révisions immuables)          │
                  │                         ├─ Résultats (publication contrôlée)     │
                  │                         ├─ Centres / postes / incidents          │
                  │                         ├─ Paiements Mobile Money                │
                  │                         └─ Audit HMAC chaîné + reporting         │
                  │  PostgreSQL 16 (+ réplica, PITR) · stockage objet médias · worker│
                  └───────────────▲─────────────────────────────────────────────────┘
                                  │ WAN HTTPS (bail signé Ed25519)
                 ┌────────────────┴──────── Centre d'examen ────────┐
                 │ Passerelle edge (FastAPI + SQLite chiffré)        │
                 │  cache médias SHA-256 · journal de réponses chaîné│
                 │  VLAN EXAM ─► postes candidats en mode kiosque    │
                 └───────────────────────────────────────────────────┘
```

## 2. Règles d'examen paramétrables et versionnées

**Problème** : constantes Python (`exam_engine.py:27-40`, `session_rules.py:13-15`).

**Cible** : table `exam_rule_sets` :

| Colonne | Rôle |
|---|---|
| `id`, `code` (ex. `B-2027-01`), `permit_category` | identification |
| `question_count`, `pass_threshold`, `duration_seconds`, `per_question_seconds?` | épreuve |
| `category_distribution` (JSON) | répartition |
| `min_pool_multiplier` | taille minimale de la banque (ex. 5) |
| `result_publication_mode` (`immediate` / `delayed` / `session_validation`), `result_delay_hours` | publication |
| `max_suspension_seconds` | incidents |
| `legal_reference`, `effective_from`, `effective_to`, `approved_by`, `approved_at` | preuve juridique |
| `status` (`draft` / `approved` / `retired`) | gouvernance (approbation à quatre yeux) |

- `exam_attempts.rule_set_id` est **figé au démarrage**, de sorte que chaque résultat soit rejugeable avec la règle qui s'appliquait.
- **Migration** : création d'un jeu `LEGACY-PROVISOIRE` qui reprend les constantes actuelles, et rattachement des tentatives existantes. Les constantes deviennent la valeur par défaut tant qu'aucun jeu n'est approuvé, ce qui ne change aucun comportement.

## 3. Banque de questions versionnée et validée

- `questions` reste l'identité stable. On ajoute `question_revisions`, **immuable** : `revision_no`, `text`, `options` [{`id`:`A`, `label`, `media_ref?`}], `correct_option_ids` (liste), `media_asset_id`, `audio_assets` par langue, `content_hash`, `status`, `reviewed_by`, `approved_by` (deux personnes distinctes).
- La trace d'examen enregistre `(question_id, revision_id)`, ce qui garantit que la correction et le recours portent sur la version vue par le candidat.
- **Banque hors dépôt** : `question_bank_gn.py` est limité à l'entraînement et à la démo. La banque officielle arrive uniquement par import signé (CSV/ZIP + empreinte SHA-256 + journal d'import) et vit en base et dans le stockage objet.
- Statistiques par question (taux de réussite, temps moyen, discrimination) calculées par un worker, pour retirer les questions défectueuses.

### Notation multi-réponses (compatible)
- Réponse candidate : `list[str]` d'identifiants d'options. Pendant la transition, le format chaîne historique est converti en `[option_id]` à la lecture.
- Juste si `set(réponse) == set(correct_option_ids)`. Option paramétrable : questions éliminatoires.
- Le scoring reste dans `exam_engine.score_answers`, réécrit et couvert par des tests de propriétés.

## 4. Examens multimédias
- Réutilise `media_storage`, `media_policy`, `official_media_readiness` et le cache edge.
- Types : `image`, `video` (lecture unique, sans contrôles de saut ; durée comptée), `audio` (énoncé en langue nationale enregistré par un locuteur validé).
- Formats cibles faible débit : WebP ≤ 150 Ko, MP4 H.264 ≤ 2 Mo, AAC/Opus 32 kb/s. Les médias de la session sont **préchargés** et vérifiés par empreinte avant le démarrage.

## 5. Reprise sécurisée après interruption
| Brique | Existant | Cible |
|---|---|---|
| Autosauvegarde | ✅ `POST /answers` (copie complète) | Envoi **incrémental** horodaté et numéroté (`seq`), acquitté |
| Chronomètre | Horloge murale | `active_seconds` : somme des intervalles actifs ; états `running` / `suspended` |
| Suspension | — | `POST /exams/{id}/suspend` et `/resume` par l'agent de centre, motif obligatoire, audit, plafond `max_suspension_seconds` |
| Expiration | Déclenchée par le client | **Tâche serveur** qui finalise toutes les tentatives échues (idempotent, réutilise `timeout-submit`) |
| Changement de poste | ✅ | Inchangé, plus l'arrêt du chrono pendant le transfert |
| Hors-ligne centre | Edge | Synchronisation du journal edge, rapprochée de la copie centrale |

## 6. Centres, postes, équipements
Existant conservé (`CenterStation`, `DeviceSession`, edge, releases signées). Ajouts :
- Mode **kiosque** du poste (navigateur verrouillé ou application edge) et émission des événements `POST /exam-monitoring/events` : perte de focus, sortie du plein écran, rechargement, perte réseau.
- **Check-list d'ouverture de session** : postes testés, médias préchargés, horloge synchronisée, onduleur. Elle est obligatoire avant le premier démarrage.

## 7. Résultats, journalisation, traçabilité
- États : `started → submitted → scored → (validated) → published`, plus `annulled` en cas de recours ou de fraude, avec motif.
- PV de session (PDF) signé par le chef de centre ; empreinte du PV dans l'audit chaîné.
- Notifications envoyées par un **outbox** transactionnel et un worker avec réessai, plutôt qu'un appel direct dans la requête.
- Signature du résultat (HMAC ou Ed25519) intégrée au QR de l'attestation.

## 8. Accessibilité et connexions instables
- WCAG 2.1 AA sur l'écran d'examen : contraste, focus, lecteur d'écran, taille de police réglable.
- Audio de l'énoncé ; temps majoré via un profil d'aménagement validé par un administrateur.
- PWA : coquille hors-ligne, budget JS de l'écran d'examen ≤ 200 Ko gzip, images adaptatives.

## 9. Reporting national et régional
Existant : `territory.py`, `/dashboard/by-center`, anomalies par centre. Cible :
vues matérialisées rafraîchies par un worker (taux de réussite par région, centre,
thème, question ; délais ; incidents), exports signés, et indicateurs de qualité
de la banque.

## 10. Dette d'architecture à résorber (sans rupture)
1. Remplacer la réécriture de `router.routes` (`routers/__init__.py`) par des routeurs uniques, une fois que les tests de contrat (`test_edge_agent_api_contract.py`) couvrent toutes les routes.
2. Rendre `create_all` bloquant ou le supprimer hors tests.
3. Centraliser le contrôle « ce candidat appartient à cet utilisateur » (aujourd'hui dupliqué, avec un repli sur l'e-mail).
4. Jetons en cookie `HttpOnly` `SameSite=Strict` ; révocation par `jti` et `token_version`.

## 11. Déploiement
- **Préproduction distincte** ; fusion dans `main` ≠ production (désactiver `autoDeployTrigger` du service de production, promotion manuelle).
- Hébergement selon la décision R18 (national ou souverain) ; la passerelle edge rend l'architecture compatible avec un hébergement central hors cloud public.
