# Guide de configuration — Paiement Mobile Money en production

Ce document décrit précisément comment activer les paiements Mobile Money
réels sur CodeRoute Guinée. Le code des opérateurs est déjà implémenté ;
il ne reste que la configuration des comptes marchands et des clés.

> **Prérequis (démarche administrative, à la charge de la DNTT)**
> Obtenir un compte marchand (merchant account) auprès de chaque opérateur.
> C'est une démarche commerciale et légale qui ne peut pas être automatisée.

---

## 1. Vue d'ensemble

Par défaut, la plateforme tourne en mode **sandbox** (paiements simulés,
aucun débit réel). Pour encaisser réellement, il faut :

1. Obtenir les identifiants marchands des opérateurs
2. Renseigner les variables d'environnement dans Render
3. Basculer `MOBILE_MONEY_MODE=production`
4. Tester un paiement réel de bout en bout avec un petit montant

Le système est protégé contre le **double-paiement** : un booking déjà
réglé ne peut jamais être débité une seconde fois (garde d'idempotence
vérifiée par test automatique).

---

## 2. Variable maîtresse

| Variable | Valeur sandbox | Valeur production |
|---|---|---|
| `MOBILE_MONEY_MODE` | `sandbox` (défaut) | `production` |

Tant que cette variable n'est pas à `production`, aucun débit réel n'a
lieu, même si les clés opérateurs sont renseignées. C'est le garde-fou
principal.

---

## 3. Orange Money Guinée

Portail développeur : https://developer.orange.com (API Orange Money)

| Variable | Description |
|---|---|
| `ORANGE_MONEY_CLIENT_ID` | Identifiant client de l'application marchande |
| `ORANGE_MONEY_CLIENT_SECRET` | Secret client (ne jamais exposer) |
| `ORANGE_MONEY_MERCHANT_KEY` | Clé marchand pour l'API Web Payment |
| `ORANGE_MONEY_BASE_URL` | URL de l'API (fournie par Orange, prod ≠ sandbox) |

Flux : OAuth2 (obtention d'un token) → initiation du paiement → polling
du statut jusqu'à `SUCCESSFULL` ou `FAILED` (timeout 30s).

---

## 4. MTN MoMo Guinée

Portail développeur : https://momodeveloper.mtn.com

| Variable | Description |
|---|---|
| `MTN_MONEY_SUBSCRIPTION_KEY` | Clé d'abonnement (Collection product) |
| `MTN_MONEY_API_USER` | API User (UUID généré) |
| `MTN_MONEY_API_KEY` | API Key associée à l'API User |
| `MTN_MONEY_BASE_URL` | `https://sandbox.momodeveloper.mtn.com` (test) ou l'URL de prod |
| `MTN_MONEY_ENVIRONMENT` | `sandbox` ou l'environnement de prod (`mtnguinee`) |

Flux : création token → `requesttopay` → polling `GET /requesttopay/{ref}`
jusqu'à `SUCCESSFUL` / `FAILED` / `REJECTED`.

---

## 5. Wave Guinée

Documentation : https://www.wave.com/en/business/api

| Variable | Description |
|---|---|
| `WAVE_API_KEY` | Clé API du compte marchand Wave |
| `WAVE_BASE_URL` | URL de l'API Wave (fournie par Wave) |

Wave est devenu un portefeuille majeur en Guinée (frais réduits). Le flux
crée une session de paiement (`checkout/sessions`) et suit son statut.

---

## 6. Opérateurs additionnels (optionnels)

Le code supporte aussi **Celcom Money** (`CELCOM_MONEY_CLIENT_ID`,
`CELCOM_MONEY_CLIENT_SECRET`, `CELCOM_MONEY_API_BASE`) et l'agrégateur
**PayDunya** (`PAYDUNYA_*`). Ils restent en sandbox tant que leurs clés
ne sont pas renseignées, sans bloquer les autres.

---

## 7. Où renseigner les clés (Render)

1. Render Dashboard → service **coderoute-backend** → onglet **Environment**
2. Ajouter chaque variable ci-dessus (ne jamais les committer dans le code)
3. Passer `MOBILE_MONEY_MODE=production`
4. Sauvegarder → le backend redéploie automatiquement

**Sécurité** : ces clés sont des secrets financiers. Ne jamais les mettre
dans le dépôt Git, dans un ticket, ou dans une capture d'écran. En cas de
fuite, les révoquer immédiatement chez l'opérateur.

---

## 8. Recette de mise en production (à faire une fois)

Avant d'ouvrir aux candidats, valider chaque opérateur avec un vrai
paiement de petit montant :

- [ ] `MOBILE_MONEY_MODE=production` activé
- [ ] Orange Money : un paiement réel aboutit à `paid` + reçu généré
- [ ] MTN MoMo : idem
- [ ] Wave : idem
- [ ] Un paiement refusé (solde insuffisant) renvoie bien `failed` sans bloquer l'app
- [ ] Un double-clic sur "Payer" ne débite qu'une fois (garde d'idempotence)
- [ ] La convocation PDF se génère après le paiement réussi
- [ ] Le reçu apparaît dans la réconciliation admin (`/payments/reconciliation`)

Comportement en cas d'incident réseau : si l'opérateur ne répond pas dans
le délai, le paiement reste `pending` avec un message invitant à la
vérification manuelle — aucun débit fantôme n'est enregistré comme `paid`.

---

## 9. Réconciliation financière

L'interface admin `/payments/reconciliation` liste les paiements,
détecte les reçus en double et permet le rapprochement comptable. À
consulter régulièrement pendant la phase pilote pour vérifier que chaque
encaissement correspond à une réservation.
