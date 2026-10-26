# Architecture cible progressive

> Audit du 26 octobre 2026 — base `main` `2b4e9b809ff27ed9111bc51c074e599e166b1793`. Lecture seule des données et du code applicatif ; fichiers d’audit uniquement. Aucune connexion à une base de production, aucun déploiement, aucune fusion.

## Principe

Conserver le monolithe modulaire FastAPI et React ; isoler les responsabilités transactionnelles avant toute extraction de microservices. Garder routes et rôles existants par façades compatibles, puis réduire les substitutions au démarrage dans des PR séparées.

## Flux critiques

| Flux | Cible | Invariant |
|---|---|---|
| Identité | Compte → rattachement candidat vérifié par identifiant | Une adresse déclarée ne transfère pas un dossier |
| Banque | Import privé → révision → validation → publication | Révision utilisée immuable, provenance et droits médias tracés |
| Tentative | Règles versionnées + trace des révisions → réponses → notation | Même copie et même correction pour une tentative, même après édition de banque |
| Finances | Intention commitée → provider avec clé stable → inbox/confirmation → règlement | Aucun paid sans preuve d’encaissement ; crash récupérable sans double débit |
| Notifications | Outbox dans transaction métier → worker avec retries | Aucun échec silencieux perdu après commit |
| Certificat | Émission versionnée, référence opaque, vérification minimale | Authenticité distincte de réussite ; révocation tracée selon DNTT |
| Exploitation | Artefact signé/testé → recette → approbation → promotion | Même SHA testé et publié, readiness bloquante |

## PostgreSQL et autorisation

Migrations additives : question_revisions, exam_rule_sets, référence de révision dans trace, payment_intents, provider_events, outbox et auth_sessions à concevoir par lots. Backfills sans requalification de résultats passés ; données ambiguës en revue manuelle. Contraintes uniques/FK et index mesurés, lock_timeout/statement_timeout adaptés.

Rôle DB applicatif distinct du rôle migration, droits minimaux, compte backup distinct. RLS éventuelle par centre après étude des relations transverses et rôles nationaux : un simple tenant_id ajouté partout ne suffit pas et risquerait de casser les autorisations. Tests négatifs de périmètre obligatoires, avec et sans pooler transactionnel.

## Exécution et résilience

API stateless multi-instance, Redis pour les usages distribués déjà présents, workers idempotents pour outbox et échéances. Ne pas déplacer le chrono ou la source d’autorité de notation dans Redis. Journal Edge signé, autorisations courtes et réconciliation centrale conservés ; aucun affaiblissement de trust store/root updater pour faire passer les tests.

Stockage privé/versionné des contenus officiels, tickets de lecture courts, médias de démo séparés. Secrets hors Git, rotation testée, clés de signature et d’audit sauvegardées de façon indépendante. Sauvegardes DB et médias chiffrées, copie hors compte, restauration en environnement isolé avec preuve applicative.

## Opérations et décision DNTT

Mesurer latence, erreurs, saturation pool, transactions inconnues, backlog outbox, tentative échue, dérive horloge Edge et âge dernière sauvegarde restaurée. Alertes routées à une astreinte avec exercice de réception.

DNTT doit valider règles, seuils, séquençage, pauses, accessibilité/aménagements, publication des résultats, validité des certificats et banque. Le jeu initial versionné doit reproduire les valeurs existantes sans les homologuer rétroactivement. Aucune nouvelle règle française n’est appliquée par analogie.
