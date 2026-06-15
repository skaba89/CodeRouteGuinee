# Alertes paiements suspects

Ce lot ajoute un endpoint de supervision pour detecter les paiements a verifier dans CodeRoute Guinee.

## Signaux controles

- Paiements `failed` et `pending`.
- Montants inhabituels.
- Plusieurs paiements sur une meme reservation.
- Numeros de recus dupliques.

Chaque consultation est journalisee avec l'action `payments.alerts_viewed`.
