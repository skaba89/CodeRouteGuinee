# Guide — Activation des notifications réelles (email, SMS, WhatsApp)

CodeRoute Guinée envoie des notifications aux candidats (confirmation de
réservation, convocation, résultat, paiement). Les trois canaux sont déjà
implémentés dans le code ; ils envoient réellement dès que leurs clés sont
configurées. Sans clés, ils retombent en mode console (log) sans jamais
bloquer l'application.

---

## 1. Vérifier l'état des canaux

Interface admin ou requête directe :

```
GET /api/v1/admin/ops/notifications-status
```

Retourne, pour chaque canal (email, sms, whatsapp) : s'il est configuré,
le fournisseur, et les variables d'environnement attendues. Un canal
`configured: false` fonctionne en mode console (aucun envoi réel).

## 2. Tester un canal avant l'ouverture

```
POST /api/v1/admin/ops/notifications-test
{ "channel": "email", "to": "votre-adresse@exemple.gn" }
```

(super_admin uniquement). Envoie un message de test. À faire une fois les
clés renseignées, pour confirmer que l'envoi réel fonctionne avant
d'ouvrir aux candidats.

---

## 3. Email — Brevo

Brevo (ex-Sendinblue) : service transactionnel fiable avec offre gratuite.

| Variable | Description |
|---|---|
| `BREVO_API_KEY` | Clé API (format `xkeysib-...`) |
| `EMAIL_FROM` | Adresse expéditrice (ex. `noreply@coderoute.gov.gn`) |
| `EMAIL_FROM_NAME` | Nom affiché (ex. `CodeRoute Guinée`) |

Étapes : créer un compte Brevo → valider le domaine expéditeur (SPF/DKIM)
→ générer une clé API → la renseigner dans Render.

## 4. SMS — Orange SMS Guinée

Portail : https://developer.orange.com (API SMS Guinée)

| Variable | Description |
|---|---|
| `ORANGE_SMS_CLIENT_ID` | Client ID OAuth2 |
| `ORANGE_SMS_CLIENT_SECRET` | Client secret |
| `ORANGE_SMS_SENDER_ADDRESS` | Numéro expéditeur provisionné (ex. `tel:+224628000000`) |
| `ORANGE_SMS_API_BASE` | `https://api.orange.com` (défaut) |

Le SMS reste le canal le plus universel en Guinée (fonctionne sur tous les
téléphones, sans internet). À privilégier pour la convocation et le résultat.

## 5. WhatsApp — Meta Cloud API

Portail : https://developers.facebook.com/docs/whatsapp/cloud-api

| Variable | Description |
|---|---|
| `WHATSAPP_PHONE_NUMBER_ID` | ID du numéro (Meta Business) |
| `WHATSAPP_ACCESS_TOKEN` | Token permanent Meta Cloud API |
| `WHATSAPP_API_BASE` | `https://graph.facebook.com/v19.0` (défaut) |

WhatsApp est très répandu en Guinée urbaine et permet des messages riches
(PDF de convocation en pièce jointe). Complémentaire du SMS.

---

## 6. Où renseigner les clés (Render)

Render Dashboard → service **coderoute-backend** → **Environment** →
ajouter les variables → sauvegarder (redéploiement automatique). Ne jamais
committer ces clés dans Git.

## 7. Stratégie recommandée par vague

- **Pilote** : email + SMS suffisent (SMS = universel, email = trace écrite).
- **National** : les trois canaux, avec le SMS comme canal garanti (couvre
  les candidats sans smartphone ni internet). Prévoir un budget SMS
  (facturé à l'envoi) proportionnel au volume de candidats.

## 8. Comportement en cas d'échec

Chaque envoi est *best-effort* : si un canal échoue (réseau, quota), l'API
ne bloque pas le parcours du candidat (la réservation/le paiement/l'examen
aboutissent quand même). Les échecs sont journalisés et remontés à Sentry.
Le candidat peut toujours retélécharger sa convocation depuis son espace.
