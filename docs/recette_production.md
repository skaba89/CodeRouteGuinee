# Checklist de recette en production — CodeRoute Guinée

Document de validation avant ouverture aux candidats. À dérouler
méthodiquement, dans l'ordre. Chaque point : une action, un résultat
attendu, une case à cocher. Noter la date, le testeur et toute anomalie.

> **Astuce** : après chaque déploiement, vider le cache du navigateur
> (Ctrl+Shift+R, ou Cmd+Shift+R sur Mac) avant de tester, sinon
> l'ancienne version peut fausser la recette.

- **Testeur :** ______________________  **Date :** ____________
- **Environnement :** ☐ Production  ☐ Pré-production
- **URL frontend :** https://coderouteguinee-frontend.onrender.com
- **URL backend :** https://coderouteguinee-backend.onrender.com

---

## 0. Pré-requis — l'application répond

| # | Action | Résultat attendu | ☐ |
|---|---|---|---|
| 0.1 | Ouvrir l'URL frontend | La page de connexion s'affiche, logo et drapeau visibles | ☐ |
| 0.2 | Ouvrir `backend/health` (ou `/docs`) | Le backend répond (statut OK) | ☐ |
| 0.3 | Se connecter en super_admin | Accès au tableau de bord admin | ☐ |

---

## 1. Parcours candidat complet (le cœur du service)

À faire de bout en bout avec un compte candidat de test.

| # | Action | Résultat attendu | ☐ |
|---|---|---|---|
| 1.1 | Inscription candidat libre | Compte créé, référence `GN-CODE-...`, connexion automatique | ☐ |
| 1.2 | Consulter les centres et créneaux | Liste des centres avec places restantes correctes | ☐ |
| 1.3 | Réserver une session | Réservation créée, référence + code de vérification affichés | ☐ |
| 1.4 | Vérifier le décompte des places | La place réservée est décomptée (une de moins) | ☐ |
| 1.5 | Payer les frais (Mobile Money) | Paiement `payé`, réservation passe à `payé` | ☐ |
| 1.6 | Télécharger la convocation PDF | PDF officiel s'ouvre (pas de « Not authenticated »), QR visible | ☐ |
| 1.7 | Démarrer l'examen depuis la réservation | 40 questions, chacune avec un visuel | ☐ |
| 1.8 | Répondre et soumettre | Résultat immédiat (score /40, admis/non admis) | ☐ |
| 1.9 | Consulter le résultat détaillé | Détail des 40 questions accessible | ☐ |
| 1.10 | Télécharger l'attestation PDF | PDF avec bandeau vert ADMIS / rouge NON ADMIS | ☐ |

---

## 2. Bloquant 1 — Validation officielle des questions

| # | Action | Résultat attendu | ☐ |
|---|---|---|---|
| 2.1 | Ouvrir la gouvernance des questions (admin) | Liste des questions avec leur statut | ☐ |
| 2.2 | Approuver (publier) une question | Statut passe à approuvé / publié | ☐ |
| 2.3 | Vérifier la synthèse de validation | Couverture par catégorie, indicateur « prêt pour examen » | ☐ |
| 2.4 | Démarrer un examen réel | Seules des questions approuvées sont tirées | ☐ |
| 2.5 | (super_admin) Rejeter une question avec motif | Statut rejeté, motif enregistré | ☐ |
| 2.6 | (admin non super) Tenter d'approuver | Refusé — l'approbation est réservée au super_admin | ☐ |

---

## 3. Bloquant 2 — Paiement Mobile Money (anti double-débit)

> En sandbox tant que les comptes marchands ne sont pas configurés.
> Passer en production uniquement après avoir renseigné les clés (voir
> `docs/mobile_money_production.md`).

| # | Action | Résultat attendu | ☐ |
|---|---|---|---|
| 3.1 | Payer une réservation | Paiement réussi | ☐ |
| 3.2 | Re-cliquer « Payer » sur la même réservation | Refusé (déjà payé) — pas de second débit | ☐ |
| 3.3 | Tenter un paiement avec un autre opérateur | Toujours refusé (idempotence) | ☐ |
| 3.4 | (Prod) Tester chaque opérateur réel avec petit montant | Orange / MTN / Wave aboutissent à `payé` + reçu | ☐ |
| 3.5 | (Prod) Vérifier la réconciliation admin | Chaque encaissement correspond à une réservation | ☐ |

---

## 4. Bloquant 3 — Sauvegarde et restauration

> Principalement automatique (CI quotidienne). Vérifications ponctuelles.

| # | Action | Résultat attendu | ☐ |
|---|---|---|---|
| 4.1 | Vérifier l'exécution du workflow de backup (GitHub Actions) | Dernière exécution en succès (vert) | ☐ |
| 4.2 | Vérifier le test de round-trip dans les logs CI | « Round-trip restore réussi » présent | ☐ |
| 4.3 | (Prod) Confirmer le stockage externe des backups | Backups répliqués hors de la CI (S3/GCS chiffré) | ☐ |

---

## 5. Bloquant 4 — Tenue en charge

| # | Action | Résultat attendu | ☐ |
|---|---|---|---|
| 5.1 | Charger l'écran de réservation (places) plusieurs fois | Réponse rapide (< 1 s), pas d'erreur | ☐ |
| 5.2 | (Avant national) Lancer un test de charge externe | Latence p95 acceptable, 0 erreur 5xx | ☐ |
| 5.3 | Vérifier le dimensionnement Render/DB pour la vague visée | Plan et `max_connections` conformes à `docs/load_testing.md` | ☐ |

---

## 6. Scan QR à l'entrée du centre

> À tester sur un appareil avec caméra (téléphone/tablette, Chrome/Android).

| # | Action | Résultat attendu | ☐ |
|---|---|---|---|
| 6.1 | Espace centre → Valider l'entrée → « Scanner la convocation » | La caméra s'ouvre avec un cadre de visée | ☐ |
| 6.2 | Présenter le QR d'une convocation | Référence + code remplis, entrée validée automatiquement | ☐ |
| 6.3 | Présenter un mauvais code (saisie manuelle) | Entrée refusée (anti-fraude) | ☐ |
| 6.4 | Sur navigateur sans caméra | Message clair + saisie manuelle disponible | ☐ |

---

## 7. Notifications (email / SMS / WhatsApp)

| # | Action | Résultat attendu | ☐ |
|---|---|---|---|
| 7.1 | Consulter l'état des canaux (admin) | Chaque canal indiqué configuré ou non | ☐ |
| 7.2 | (Prod) Envoyer une notification de test par canal | Message reçu réellement (email/SMS/WhatsApp) | ☐ |
| 7.3 | Faire une réservation, vérifier la notification | Confirmation reçue (ou log console si non configuré) | ☐ |
| 7.4 | Couper un canal (mauvaise clé) et refaire une action | Le parcours candidat aboutit quand même (best-effort) | ☐ |

---

## 8. Tableau de bord de supervision nationale

| # | Action | Résultat attendu | ☐ |
|---|---|---|---|
| 8.1 | Admin → tableau de bord | Synthèse nationale (centres, sessions, examens, incidents) | ☐ |
| 8.2 | Consulter l'activité par centre | Chaque centre listé avec sessions, réservations, examens | ☐ |
| 8.3 | Vérifier les taux de réussite | Colorés (vert ≥ 70 %, orange ≥ 50 %, rouge sinon) | ☐ |
| 8.4 | Trier par colonne (examens, réservations) | Le tri fonctionne | ☐ |

---

## 9. Mode hors-ligne (entraînement)

| # | Action | Résultat attendu | ☐ |
|---|---|---|---|
| 9.1 | Lancer un entraînement en ligne une fois | Questions chargées | ☐ |
| 9.2 | Couper la connexion (mode avion), relancer l'entraînement | L'entraînement fonctionne (questions en cache) | ☐ |
| 9.3 | Vérifier la bannière hors-ligne | Bandeau discret indiquant l'état hors ligne | ☐ |
| 9.4 | Hors ligne, tenter une réservation | Correctement indisponible (nécessite le réseau) | ☐ |

---

## 10. Rendu mobile

> À tester sur un vrai téléphone ou en mode mobile du navigateur (F12).

| # | Action | Résultat attendu | ☐ |
|---|---|---|---|
| 10.1 | Écran d'examen sur mobile | Visuel au-dessus de la question, tout lisible | ☐ |
| 10.2 | Grille des 40 numéros sur mobile | Tient sur la largeur, cliquable au doigt | ☐ |
| 10.3 | Formulaires (inscription, paiement) sur mobile | Champs empilés, confortables | ☐ |
| 10.4 | Carte de résultat sur mobile | Score centré, lisible | ☐ |

---

## 11. Sécurité et rôles

| # | Action | Résultat attendu | ☐ |
|---|---|---|---|
| 11.1 | Candidat tente d'accéder au tableau de bord admin | Refusé (403) | ☐ |
| 11.2 | Candidat tente de démarrer la réservation d'un autre | Refusé (403) | ☐ |
| 11.3 | Auto-école non validée tente de se connecter | Refusé tant que non activée par la DNTT | ☐ |
| 11.4 | Session complète : nouvelle réservation | Refusée (session complète) | ☐ |
| 11.5 | Vérifier HTTPS et en-têtes de sécurité | Connexion chiffrée, en-têtes présents | ☐ |

---

## 12. Points administratifs (hors code, à confirmer avant national)

| # | Élément | Fait | ☐ |
|---|---|---|---|
| 12.1 | Les 200 questions validées officiellement par la DNTT | | ☐ |
| 12.2 | Comptes marchands Mobile Money obtenus et clés configurées | | ☐ |
| 12.3 | Clés de notification renseignées (Brevo / Orange / Meta) | | ☐ |
| 12.4 | Stockage externe des backups configuré | | ☐ |
| 12.5 | Secrets de production tournés (voir `SECURITY_ROTATION.md`) | | ☐ |
| 12.6 | Plan Render / base dimensionnés pour la vague de déploiement | | ☐ |

---

## Décision de mise en production

- ☐ **GO** — tous les points bloquants (sections 1 à 5, 11) sont validés
- ☐ **GO conditionnel** — anomalies mineures listées ci-dessous, corrigées après lancement
- ☐ **NO-GO** — anomalies bloquantes, à corriger avant ouverture

**Anomalies relevées :**

```
_______________________________________________________________
_______________________________________________________________
_______________________________________________________________
```

**Validé par :** ______________________  **Signature / date :** ____________

---

*Rappel des vagues recommandées (voir `docs/load_testing.md`) : Vague 1
pilote 1-3 centres Conakry → Vague 2 régional 10-20 centres → Vague 3
national 135 centres. Ne pas viser le national sans avoir validé les
vagues 1 et 2 en conditions réelles.*
