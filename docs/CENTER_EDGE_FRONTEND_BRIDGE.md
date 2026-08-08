# Center Edge — Frontend Bridge et Claim candidat

## Objectif

Permettre au frontend national CodeRoute de basculer sur le gateway LAN sans exposer le token opérateur, sans dupliquer l'ExamPage et sans calculer le résultat dans le centre.

## Chaîne de confiance

```text
DNTT central
   ↓ lease signé + poste signé
Gateway Edge
   ↓ claim secret temporaire
Poste candidat correspondant
   ↓ token session Edge
ExamPage existante
   ↓ réponses locales hash-chaînées
Gateway Edge
   ↓ sync signée au retour WAN
DNTT central → score officiel
```

## Activation et claim

`POST /operator/leases` retourne un claim temporaire et une `candidate_url`, jamais le token candidat. Le frontend lit le fragment `#/exam?edge=...` avant le rendu React, efface immédiatement le secret de l'URL, puis réclame la session auprès de `/v1/claim` avec le `device_key` persistant du poste.

Le claim est retryable tant que le premier appel candidat authentifié n'a pas réussi. Après ce premier appel, il devient définitivement inutilisable.

## Stockage navigateur

Le token Edge reste uniquement dans `sessionStorage`, lié à `attempt_id`. Il n'est jamais écrit dans l'URL, le localStorage durable, les logs ou le cache Service Worker.

## Bridge réseau

`edgeExamFetchBridge.ts` intercepte uniquement les appels d'examen nécessaires pour la tentative Edge active. Les autres appels restent sur l'API nationale. L'ExamPage existante reste inchangée.

## Finalisation et résultat

Une soumission Edge finalise le journal local puis affiche `Résultat officiel en attente de synchronisation DNTT`. Aucun score ni verdict n'est calculé dans le centre. `/results` n'est jamais intercepté : ADMIS/AJOURNÉ n'est affiché qu'après réponse du serveur central.

## Tests

Les tests couvrent claim chiffré, mauvais poste, retry/consommation/expiration, suppression du secret de l'URL, session navigateur, redirection pending et absence de verdict local.

## Étape suivante

P6 — Center Operations UI : état WAN/gateway, postes prêts, activation lease par poste, QR claim, cache média, sync/retry et incidents DNTT.
