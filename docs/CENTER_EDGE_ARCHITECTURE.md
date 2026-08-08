# CodeRoute Center Edge — architecture de continuité nationale

## Objectif

Le mode **Center Edge** permet à un centre d'examen de continuer une épreuve officielle lorsque la liaison Internet/WAN vers la plateforme nationale devient instable ou indisponible.

La règle de sécurité centrale est non négociable : **la banque officielle complète et les bonnes réponses ne sont jamais mises en cache dans le navigateur candidat**. Le PWA reste réservé aux contenus pédagogiques d'entraînement. Le gateway local est un composant institutionnel enrôlé, surveillé et révocable.

## Menaces traitées

- coupure Internet en cours d'examen ;
- perte de paquets / latence forte ;
- redémarrage contrôlé d'un poste candidat ;
- usurpation d'un faux gateway ;
- replay d'un ancien heartbeat ;
- gateway volé ou compromis ;
- utilisation d'une clé Edge dans un autre centre.

## Phase 1 — identité de confiance du gateway

Implémentée dans le lot `Center Edge Trust Foundation`.

### 1. Génération locale de la clé

Sur le PC/serveur local dédié du centre :

```bash
python scripts/generate_edge_identity.py --label "Gateway Edge Ratoma"
```

Le script génère une paire **Ed25519** :

- `.coderoute-edge/private-key.pem` : reste uniquement sur le gateway ;
- `.coderoute-edge/public-key.txt` : peut être communiquée à la DNTT ;
- `.coderoute-edge/identity.json` : fingerprint et métadonnées locales.

La clé privée ne doit jamais être copiée dans Git, Render, Neon ou le navigateur candidat.

### 2. Enrôlement institutionnel

Un `admin` ou `super_admin` enregistre la clé publique :

```http
POST /api/v1/center-edge/nodes
Authorization: Bearer <admin>

{
  "center_id": "<centre>",
  "label": "Gateway Edge Salle A",
  "public_key_b64": "<clé publique>",
  "capabilities": ["exam-lease-v1", "answer-journal-v1", "media-prefetch-v1"]
}
```

Le serveur stocke uniquement :

- le centre ;
- le fingerprint SHA-256 ;
- la clé publique ;
- les capacités déclarées ;
- la dernière séquence de heartbeat ;
- la dernière version logicielle / dernière présence.

L'enrôlement est journalisé dans la chaîne d'audit tamper-evident.

### 3. Heartbeat signé

Le gateway signe le payload canonique avec sa clé privée Ed25519.

```json
{
  "node_id": "...",
  "center_id": "...",
  "sequence": 42,
  "sent_at": "2026-08-08T20:00:00Z",
  "software_version": "edge-0.1.0",
  "capabilities": ["answer-journal-v1", "exam-lease-v1"]
}
```

Puis appelle :

```http
POST /api/v1/center-edge/heartbeat
```

Le backend vérifie :

1. nœud connu ;
2. nœud actif ;
3. centre identique ;
4. signature Ed25519 valide ;
5. dérive d'horloge <= 5 minutes ;
6. séquence strictement supérieure à la dernière valeur acceptée.

Un heartbeat replayé est rejeté.

### 4. Suspension et révocation

- `suspended` : arrêt temporaire ; la même clé peut être réactivée par l'autorité ;
- `revoked` : définitif. Une clé compromise n'est jamais réactivée ; il faut générer une nouvelle paire et enrôler un nouveau nœud.

## Phase 2 — lease d'examen hors ligne

À implémenter immédiatement après la fondation de confiance.

Le serveur central délivrera un **lease par tentative**, uniquement après :

1. réservation payée ;
2. check-in physique ;
3. Center Gate validé ;
4. poste candidat autorisé ;
5. gateway Edge actif et heartbeat récent.

Le lease contiendra :

- `lease_id` unique ;
- tentative / session / centre ;
- `started_at` et `deadline_at` émis par le serveur central ;
- trace des questions de CETTE tentative seulement ;
- textes/options/médias nécessaires ;
- hash SHA-256 de la trace ;
- signature du serveur central ;
- **aucune bonne réponse**.

Le gateway conservera ce lease dans son stockage local chiffré et n'exposera au navigateur que la tentative concernée.

## Phase 3 — journal de réponses signé

En cas de coupure WAN :

1. le navigateur candidat envoie les réponses au gateway LAN ;
2. le gateway écrit un journal append-only : numéro de séquence, temps monotone, question, réponse, hash précédent ;
3. à la fin du temps, le gateway ferme localement le lease ;
4. le gateway signe le hash final avec sa clé Ed25519 ;
5. dès le retour Internet, il synchronise le journal au serveur central ;
6. le serveur central vérifie signature + lease + séquences + deadline ;
7. **le scoring reste exclusivement central** avec la trace officielle en base.

Cette conception permet une finalisation après retour réseau sans faire confiance à l'horloge du navigateur.

## Phase 4 — cache média de centre

Les images/vidéos nécessaires à une session devront être préchargées par le gateway avant l'ouverture du centre :

- cache par hash de contenu ;
- manifeste signé ;
- contrôle MIME/taille/hash ;
- suppression automatique après rétention ;
- aucune URL admin ni clé de correction dans le cache.

Le navigateur candidat récupère les médias via le LAN du centre, pas directement depuis le CDN lorsque le WAN est indisponible.

## Readiness d'un centre Edge

Un centre ne doit être déclaré `offline-capable` que si :

- au moins un gateway `active` ;
- heartbeat < 3 minutes ;
- horloge synchronisée ;
- version logicielle autorisée ;
- clé non révoquée ;
- stockage local chiffré opérationnel ;
- dernier test de synchronisation réussi ;
- médias de la session préchargés ;
- procédure opérateur testée.

## Exploitation nationale

Recommandations :

- 1 gateway principal + 1 secours dans les grands centres ;
- UPS/onduleur pour gateway + switch LAN + routeur ;
- NTP local/fiable ;
- réseau candidat séparé du réseau administratif ;
- firewall : le gateway n'accepte que les postes du VLAN examen ;
- rotation de clé annuelle ou après incident ;
- révocation immédiate en cas de vol/compromission ;
- exercice de coupure WAN au minimum avant chaque campagne nationale majeure.

## Ce que le Center Edge ne doit jamais faire

- distribuer toute la banque officielle à tous les navigateurs ;
- stocker les bonnes réponses côté client ;
- calculer le résultat administratif final localement ;
- accepter une tentative sans check-in/lease central préalable ;
- permettre à une clé révoquée de revenir en service ;
- faire confiance à `Date.now()` du navigateur comme preuve de deadline.
