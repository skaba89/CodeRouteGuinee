# PAY-01 — Bloquer les paiements simulés en production

Base : `main` @ `9a933cd9608fcb92712844b103d0f86284d6556f`.
Branche : `fix/p0-production-payment-mode`.
Le plan de PRODUCTION_ROADMAP.md a été validé par « continuer » dans la session.
Statut : correction proposée en PR, aucune fusion ni mise en production.

## Comportement

- `Settings.validate_production_secrets()` refuse le démarrage si l’environnement est production et le mode Mobile Money n’est pas production. Casse et espaces périphériques sont normalisés.
- Le dispatcher applique une garde indépendante, avant tout appel simulé ou réel, y compris si le cache Settings avait été construit dans un autre environnement. Il prend les valeurs effectives des variables d’environnement, avec repli sur Settings (configuration dotenv incluse).
- PayDunya en production exige son propre mode `live`. MTN exige une cible explicite hors test/sandbox et une URL HTTPS hors hôte sandbox ; les valeurs par défaut de ces providers ne suffisent plus.
- Les simulations en développement, test et staging restent possibles. Les contrats des quatre providers réels sont conservés et testés avec des fonctions factices.
- À titre défensif, si le garde de démarrage est contourné, l’API conserve son contrat actuel : réponse 201 contenant un paiement `failed`, sans `paid_at`, et réservation non réglée. Aucun fournisseur n’est appelé sur une configuration bloquée.

## Fichiers et impacts

Code : `backend/app/core/config.py`, `backend/app/payment_provider_dispatcher.py`.
Tests : nouvelle matrice `backend/tests/test_production_payment_mode.py`, adaptation des configurations valides dans `test_production_secrets.py` et `test_ha_config.py`.
Exploitation : modèle `deploy/vps/.env.vps.example` et procédure `deploy/vps/README.md`.
Aucune migration, modification de tarif, permission, remboursement ou règle d’examen.
Aucune clé opérateur réelle n’a été utilisée ou ajoutée.

## Validation

152 tests réussis, 45 avertissements, 8,96 secondes sur SQLite jetable : nouvelle matrice de configuration/défense runtime, configuration production et HA, dispatcher, invariants de sécurité financière, cotation, idempotence, remboursements, parcours finance et exposition des ports. Ruff sur les cinq fichiers Python modifiés : aucun écart ; `git diff --check` : aucun écart.

Commande depuis `backend/` avec Python 3.12 et les dépendances du dépôt :

```bash
PYTHONPATH=. DATABASE_URL=sqlite+pysqlite:///:memory: AUTO_CREATE_TABLES=true ENVIRONMENT=test \
python ../docs/audit/evidence/pay01/run_tests_offline.py \
  tests/test_production_payment_mode.py tests/test_production_secrets.py \
  tests/test_ha_config.py tests/test_payment_provider_dispatcher.py \
  tests/test_payment_security_invariants.py tests/test_payment_quote.py \
  tests/test_payment_idempotency_lifecycle.py tests/test_payment_refund_workflow.py \
  tests/test_e2e_admin_finance.py tests/test_compose_port_exposure.py \
  -q --tb=short --disable-warnings
```

Le harness désactive Sentry/OpenTelemetry et interdit les connexions TCP/IP du processus de tests, sans modifier le code applicatif. Il est destiné à ces tests en processus ; il n’isole pas d’éventuels processus enfants ni les outils natifs. Cette validation ciblée n’est ni la suite complète, ni un test PostgreSQL, ni une certification de fournisseur réel. Les suites CI complètes et PostgreSQL doivent compléter la validation de la PR ; aucun succès de ces suites n’est anticipé ici.

## Avant promotion et retour arrière

Une ancienne `.env.vps` en sandbox fera volontairement échouer le démarrage. Préparer la configuration et les contrats opérateurs en recette avant toute promotion manuelle. Ne pas basculer une démo en production pour conserver les simulations, ni considérer que changer le mode configure les identifiants.

Ne pas reclasser ou supprimer les paiements historiques : rapprochement et décision métier séparés. Aucun rollback de données n’est nécessaire. En cas de problème de configuration réelle, bloquer les nouveaux paiements et corriger la configuration ; ne pas réintroduire une confirmation simulée en production.

## Limites restantes

Les gardes ne certifient ni les contrats, ni le bénéficiaire, ni la devise, ni l’authenticité d’un endpoint arbitraire configuré par un opérateur. La confirmation des webhooks, les clés d’idempotence fournisseur et la fenêtre crash/commit restent les lots PAY-02/PAY-03. Les autres constats de l’audit restent ouverts. Le fichier Render est inactif : il n’a pas été modifié par ce correctif.
