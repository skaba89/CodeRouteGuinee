# API rapprochement financier

Endpoint ajoute sur la branche `finance-ui-filters53` :

`GET /api/v1/payments/admin/reconciliation/items`

Parametres :
- `provider`
- `status`
- `date_from`
- `date_to`
- `limit`

Acces reserve aux roles `admin` et `super_admin`.
