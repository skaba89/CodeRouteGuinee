---
name: security-review
description: Revue sécurité CodeRoute d'un diff ou d'un périmètre — authentification, rôles et périmètre centre, IDOR, fuite de la banque et des clés de correction, résultats, paiements, uploads, secrets, données personnelles.
---

# Revue de sécurité

Ne rapporter que des failles **vérifiées** : scénario d'exploitation concret, impact, correctif minimal, test de régression attendu.

## Liste de contrôle
- **Rôles** : chaque route a `require_roles(...)` ; un agent `center` est limité à `current_user.center_id` ; un candidat à son propre dossier (`user_id`, jamais un nouvel accès par e-mail).
- **IDOR** : tout identifiant reçu (tentative, réservation, candidat, centre, poste) est rattaché au périmètre de l'appelant.
- **Clés de correction** : aucune sortie de `correct_answer` / `correct_option_ids` / `explanation` vers `candidate` ou `center`, y compris dans les erreurs, exports, PDF et notifications.
- **Banque** : aucune question officielle ajoutée au dépôt ni au bundle frontend.
- **Résultats** : pas de publication ni de notification avant l'état autorisé ; écriture via l'audit chaîné.
- **Authentification** : 2FA des rôles privilégiés, durée des jetons, révocation, limitation des tentatives.
- **Paiements** : montant calculé côté serveur, webhook signé, idempotence, séparation des tâches sur les remboursements.
- **Injection / XSS** : SQL paramétré uniquement ; pas de `dangerouslySetInnerHTML` sur une donnée utilisateur ; médias HTTPS et types contrôlés.
- **Secrets** : rien dans le code, les tests, la CI ou les logs ; `.env*` réels jamais lus.
- **Données personnelles** : minimisation, pseudonymisation dans les logs, export journalisé.

Référence : `docs/audit/PLAN_SECURITE.md`.
