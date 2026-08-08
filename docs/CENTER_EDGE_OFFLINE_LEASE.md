# Center Edge Offline Lease v1

## But

Permettre à une tentative officielle **déjà démarrée et autorisée** de survivre à une coupure WAN du centre sans exposer la banque globale ni la clé de correction.

Ce protocole complète `CENTER_EDGE_ARCHITECTURE.md` et repose sur la fondation Ed25519 du gateway.

## 1. Émission du lease

Le gateway doit être :

- enrôlé ;
- `active` ;
- rattaché au même centre que la session ;
- visible par un heartbeat récent ;
- doté de la capacité `exam-lease-v1` dans l'exploitation cible.

Il signe une requête `lease.issue` avec sa clé Ed25519.

Le serveur central refuse l'émission si :

- la tentative n'est pas `started` ;
- la deadline est déjà passée ;
- le centre ne correspond pas ;
- la trace officielle est absente/incomplète ;
- un autre gateway détient déjà le lease de cette tentative ;
- `EDGE_LEASE_SIGNING_SECRET` n'est pas configuré.

## 2. Contenu du lease

Le lease est **strictement limité à une tentative** et contient :

- lease/node/center/session/attempt/candidate IDs ;
- référence candidat minimale ;
- `started_at`, `deadline_at`, durée ;
- trace officielle et hash de banque ;
- les questions sélectionnées dans l'ordre de la trace ;
- texte, options, image/vidéo/audio nécessaires.

Il ne contient jamais :

- `correct_answer` ;
- `explanation` ;
- toute la banque officielle ;
- des secrets serveur.

Le paquet est signé en **Ed25519** par le serveur central avec une clé déterministe dérivée de `EDGE_LEASE_SIGNING_SECRET`.

Le gateway peut récupérer la clé publique via :

```http
GET /api/v1/center-edge/lease-signing-key
```

Avant de servir le lease sur le LAN, il doit vérifier la signature.

## 3. Journal de réponses hors ligne

Pendant la coupure WAN, chaque modification de réponse devient un événement append-only :

```json
{
  "sequence": 17,
  "elapsed_ms": 442013,
  "question_id": "...",
  "answer": "...",
  "prev_hash": "...",
  "event_hash": "..."
}
```

`event_hash` est le SHA-256 canonique de :

- lease_id ;
- sequence ;
- elapsed_ms ;
- question_id ;
- answer ;
- prev_hash.

Propriétés vérifiées par le serveur :

- séquence continue à partir de 1 ;
- temps monotone non décroissant ;
- question incluse dans le lease ;
- réponse incluse dans les options du lease ;
- chaîne `prev_hash` intacte ;
- hash de chaque événement exact ;
- head final exact ;
- finalisation dans la durée du lease (+ 2 secondes de tolérance technique).

## 4. Synchronisation après retour WAN

Après reconnexion :

1. le gateway rétablit son heartbeat ;
2. il signe une requête `lease.offline_sync` ;
3. la signature engage `lease_id`, temps final, head du journal et nombre d'événements ;
4. le serveur vérifie le journal ;
5. le serveur revalide la trace et le snapshot de correction ;
6. le serveur reconstruit les dernières réponses ;
7. **le serveur central calcule le score** ;
8. la tentative passe à `submitted` ;
9. la preuve est enregistrée dans l'audit chainé.

Le champ administratif `submitted_at` correspond au temps de finalisation prouvé par le lease (`started_at + finalized_elapsed_ms`), tandis que `synced_at` conserve le moment réel du retour réseau.

## 5. Snapshot de correction

À l'émission, le serveur stocke en interne un hash de la clé de correction sélectionnée. Ce hash n'est **pas retourné au gateway**.

À la synchronisation, le serveur le recalcule. Si une bonne réponse a changé entre les deux moments :

```text
EDGE_SCORING_SNAPSHOT_CHANGED
```

La notation automatique est bloquée et le cas doit passer en traitement institutionnel.

## 6. Idempotence

Une synchronisation réussie peut être rejouée avec une **nouvelle séquence de requête Edge** et le même `journal_head_hash`.

Le serveur retourne alors le résultat existant sans :

- rescoring ;
- second incrément du nombre de tentatives ;
- duplication du résultat.

Un même lease présenté ensuite avec un autre journal est refusé.

## 7. Sécurité de la clé centrale

Variable obligatoire en production :

```text
EDGE_LEASE_SIGNING_SECRET
```

Exigences :

- minimum 32 caractères aléatoires ;
- identique sur toutes les instances API ;
- ne jamais exposer au gateway ;
- sauvegardée dans le coffre de secrets de l'infrastructure ;
- rotation planifiée entre campagnes, pas au milieu de leases actifs sans procédure de multi-key verification.

## 8. Ce que ce lot ne fait pas encore

Le protocole central est prêt, mais le **daemon local du gateway** reste à construire. Le prochain lot doit fournir :

- service local FastAPI/SQLite ;
- stockage chiffré des leases ;
- API LAN uniquement ;
- journal append-only sur disque ;
- cache média par hash ;
- file de synchronisation ;
- écran opérateur de santé du gateway ;
- verrouillage réseau/VLAN.

Le navigateur candidat ne devra jamais appeler directement l'API centrale pour le mode hors ligne : il parlera au daemon Edge sur le LAN du centre.
