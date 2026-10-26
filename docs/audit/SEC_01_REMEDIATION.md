# SEC-01 — Interdire le seed pilote en production

Base : main @ `1cf1c0c78b945792f318f9526fe98f606141be9b`.
Branche : `fix/p0-pilot-seed-production-guard`.
Statut : correction proposée, aucune fusion ni mise en production effectuée par cette session.

## Plan et réalisation

Périmètre limité à `backend/app/seed_pilote_conakry.py` et
`backend/tests/test_seed_pilot_safety.py` : ajouter une garde avant SessionLocal,
préserver le développement et les bases jetables explicitement autorisées,
vérifier le refus même avec une dérogation ou un mot de passe personnalisé.
Aucune modification du modèle métier, des données, des permissions API ou des
règles DNTT. La documentation du script ne préconise plus un lancement en production.
Les imports sont normalisés et une variable de boucle inutilisée est préfixée `_`.

La garde lit l’environnement effectif, avec repli sur Settings, et normalise casse
et espaces. Production est toujours refusée ; ALLOW_DEMO_SEED_NON_DEV ne permet
aucune exception en production. Hors développement, cette variable doit être
explicitement true pour autoriser une base jetable. La garde s’exécute avant
la création d’une session DB et avant toute insertion de questions, comptes,
candidats ou réservations.

## Validation

32 tests réussis, 14 avertissements, 5,69 secondes :

- production avec casse/espaces variables et dérogation absente/true/false ;
- cache Settings construit en développement puis environnement production ;
- configuration production issue de Settings sans override ENVIRONMENT ;
- absence vérifiée de création de session et d’appel au seed de questions ;
- lancement réel `python -m app.seed_pilote_conakry` dans un sous-processus
  avec environnement minimal explicite, base SQLite mémoire et télémétrie désactivée ;
- usages autorisés : développement et staging/test explicitement jetables ;
- régressions des seeds génériques et du parcours de démonstration DNTT.

Depuis backend/, avec Python 3.12 et les dépendances du dépôt :

```bash
PYTHONPATH=. DATABASE_URL=sqlite+pysqlite:///:memory: AUTO_CREATE_TABLES=true ENVIRONMENT=test \
python ../docs/audit/evidence/pay01/run_tests_offline.py \
  tests/test_seed_pilot_safety.py tests/test_seed_demo_safety.py \
  tests/test_seed_demo_dntt.py -q --tb=short --disable-warnings
ruff check app/seed_pilote_conakry.py tests/test_seed_pilot_safety.py
```

Ruff : aucun écart ; git diff --check : aucun écart.
Les sorties sont conservées dans evidence/sec01/pytest.txt.
Ces contrôles ciblés ne sont pas une nouvelle exécution de la suite complète.
Aucun accès à une base métier et aucun appel fournisseur réel.

## Impact et retour arrière

Le script ne constitue plus une méthode de provisionnement de production.
Utiliser bootstrap_admin et les imports officiels après validation institutionnelle.
Aucun compte historique n’est supprimé, désactivé ou réattribué ; leur éventuelle
présence en production reste à vérifier avec l’exploitant.

Aucune migration ni restauration de données n’est nécessaire. Un retour à une
version antérieure réintroduirait ce risque ; conserver l’interdiction des seeds
de démonstration dans les procédures d’exploitation.

## Suivi

La PR PAY-01 #264 est fusionnée ; ses six workflows, dont Fullstack Business E2E,
ont réussi sur son commit d32187c97b6ee95484caf796dc315f67c10e0002.
Cela ne prouve pas son déploiement sur le VPS. Le prochain P0 applicatif est
l’immuabilité des questions et corrections associées à une tentative (EX-01),
qui nécessite un plan de migration et de compatibilité avant implémentation.
