# P8 — Release Management sécurisé des gateways Center Edge

## 1. Objectif

P8 industrialise la mise à niveau des gateways Center Edge sans transformer le daemon d'examen en outil d'administration distante arbitraire.

La chaîne est volontairement séparée en trois responsabilités :

```text
DNTT Control Plane
  │ manifeste signé Ed25519
  │ + URL HTTPS + SHA-256 + taille
  ▼
Edge Agent non privilégié
  │ vérification signature
  │ téléchargement isolé
  │ contrôle SHA-256 / taille
  │ staging seulement
  ▼
Updater local à privilèges minimaux
  │ re-vérification artefact
  │ extraction sécurisée
  │ bascule atomique current/previous
  ▼
Attestation signée vers DNTT
```

Le daemon web ne reçoit pas le socket Docker, ne lance pas de commande shell fournie par le serveur central et ne remplace jamais lui-même son code en cours d'exécution.

## 2. Racine de confiance

Les leases d'examen et les releases utilisent le même secret institutionnel `EDGE_LEASE_SIGNING_SECRET` mais **pas la même clé Ed25519**.

La clé release est dérivée avec un domaine distinct :

```text
SHA-256("coderoute-edge-release-v1\0" || EDGE_LEASE_SIGNING_SECRET)
```

Cela empêche la confusion cryptographique entre un manifeste logiciel et un lease d'examen.

Le gateway récupère uniquement la clé publique via :

```text
GET /api/v1/center-edge/release-signing-key
```

La clé privée n'est jamais transmise aux centres.

## 3. Manifeste signé

Une release contient notamment :

- `release_id` ;
- `software_version` ;
- format `tar.gz` ;
- URL HTTPS ;
- SHA-256 exact ;
- taille exacte ;
- date de création ;
- version minimale actuellement installée ;
- notes de release.

L'URL de l'artefact ne peut pas contenir d'identifiants, pointer vers localhost, `.local` ou une IP littérale privée/réservée.

Le gateway revalide également l'URL et chaque redirection avant téléchargement.

## 4. Contrat de l'artefact

L'archive doit contenir au minimum :

```text
edge_agent/
  requirements.txt
  coderoute_edge/
    __init__.py
    ...
```

Le build national doit produire un artefact reproductible ou, au minimum, traçable avec :

- SHA-256 publié dans le manifeste ;
- taille exacte ;
- commit Git source ;
- version logicielle ;
- SBOM à ajouter dans le chantier supply-chain suivant ;
- stockage HTTPS institutionnel ou object storage contrôlé.

P8 ne publie pas encore automatiquement un vrai artefact de production. Il fournit la chaîne de confiance et le control plane nécessaires pour le faire sans contourner la sécurité.

## 5. États d'une release

| État | Signification |
|---|---|
| `draft` | manifeste créé mais invisible aux gateways |
| `canary` | uniquement les `node_id` explicitement autorisés |
| `rolling` | pourcentage déterministe de la flotte |
| `released` | diffusion nationale autorisée |
| `paused` | aucune nouvelle installation proposée |
| `rollback` | retour ordonné vers une release antérieure signée |
| `revoked` | release définitivement interdite |

Une release révoquée ne peut pas être réactivée.

## 6. Sélection déterministe des vagues

Le rollout utilise :

```text
SHA-256(release_id + ":" + node_id) % 100
```

Un gateway reste donc dans la même vague lors des appels successifs.

Cela évite une sélection aléatoire changeante qui rendrait les incidents difficiles à reproduire.

## 7. Quality gate obligatoire

Le serveur central contrôle les promotions, même si l'interface est contournée.

### Démarrage canary

Tous les gateways canary doivent être :

- enrôlés ;
- actifs ;
- actuellement en ligne.

### Canary → rolling

100 % des gateways de la vague canary doivent avoir attesté `installed`.

`staged` ne suffit pas.

### Rolling → vague supérieure

Au moins 80 % des gateways éligibles de la vague précédente doivent avoir attesté `installed`.

### Passage national

Le statut `released` exige une vague `rolling` préalable d'au moins 50 % validée.

### Échec

Une attestation `failed` sur une release `canary`, `rolling` ou `released` provoque automatiquement :

```text
rollout_status = paused
```

La diffusion s'arrête côté serveur sans dépendre d'une action humaine dans le navigateur.

Une release avec échec ou rollback dans la vague précédente ne peut pas être promue.

## 8. Check machine

Le gateway appelle :

```text
POST /api/v1/center-edge/release/check
```

La requête est signée par la clé Ed25519 propre au gateway et contient :

- `node_id` ;
- `center_id` ;
- séquence anti-replay ;
- timestamp ;
- version courante.

Le central exige également un heartbeat récent.

Une release `draft`, `paused` ou `revoked` n'est jamais proposée.

## 9. Staging non privilégié

L'agent :

1. vérifie la signature du manifeste ;
2. vérifie `min_current_version` ;
3. crée un client HTTP séparé sans cookie/token du central ;
4. refuse les redirections non HTTPS ou vers des destinations interdites ;
5. télécharge en streaming ;
6. vérifie la taille ;
7. calcule SHA-256 ;
8. supprime le fichier temporaire en cas d'erreur ;
9. renomme atomiquement l'artefact vérifié ;
10. écrit `staged.json` ;
11. atteste `staged` auprès de la DNTT.

Variables :

```text
CODEROUTE_EDGE_RELEASE_DIR=.coderoute-edge/releases
CODEROUTE_EDGE_MAX_RELEASE_BYTES=536870912
CODEROUTE_EDGE_SOFTWARE_VERSION=edge-agent-0.3.0
CODEROUTE_EDGE_TARGET_VERSION=edge-agent-0.3.0
```

## 10. Updater local

L'installation n'est pas exposée comme endpoint HTTP.

Commande :

```bash
PYTHONPATH=edge_agent python edge_agent/scripts/apply_verified_release.py \
  --release-root /opt/coderoute-edge/releases
```

L'updater :

- relit `staged.json` ;
- exige `verified=true` ;
- recalcule SHA-256 et taille ;
- refuse path traversal ;
- refuse symlinks, hardlinks, périphériques et FIFO contenus dans le tar ;
- limite le volume décompressé ;
- valide le layout applicatif ;
- installe dans `versions/<software_version>` ;
- refuse qu'un lien `current` ou `previous` sorte de `versions/` ;
- bascule `current` atomiquement ;
- conserve la version précédente ;
- écrit `install-receipt.json`.

Le service système chargé d'exécuter cet updater doit disposer uniquement des droits nécessaires sur le répertoire de versions et le redémarrage du service Edge. Il ne doit pas être pilotable directement depuis le navigateur candidat.

## 11. Attestation après installation

Après installation/restart, l'agent lit le reçu et appelle :

```text
POST /api/v1/center-edge/release/attest
```

Résultats supportés :

- `staged` ;
- `installed` ;
- `failed` ;
- `rolled_back`.

Chaque attestation est signée par la clé du gateway et stockée dans la gouvernance institutionnelle centrale.

La console DNTT affiche par release :

- nombre de nœuds éligibles ;
- staged ;
- installed ;
- failed ;
- rolled_back ;
- détail par gateway et centre.

## 12. Rollback

Le rollback ne crée jamais un paquet improvisé.

La release fautive contient un `rollback_release_id` qui doit pointer vers une release antérieure déjà signée et connue du control plane.

Le gateway reçoit alors :

```text
action = rollback
```

avec le manifeste signé de la version de secours.

L'updater peut aussi rebascule localement vers `previous` lorsque cette version a déjà été installée et vérifiée :

```bash
PYTHONPATH=edge_agent python edge_agent/scripts/apply_verified_release.py \
  --release-root /opt/coderoute-edge/releases \
  --rollback
```

## 13. Console DNTT

La console P8 est intégrée au dashboard national P7.

### Admin

Lecture seule : manifests, statut, empreinte, rollout et attestations.

### Super-admin

Peut :

- créer un manifest `draft` ;
- choisir les gateways canary parmi les nœuds sains/en ligne ;
- lancer canary ;
- passer à 10 %, 25 %, 50 % ;
- ouvrir 100 % national lorsque le quality gate le permet ;
- mettre en pause ;
- ordonner un rollback ;
- révoquer définitivement une release.

Le backend reste l'autorité : masquer un bouton dans React ne constitue jamais la protection principale.

## 14. Procédure recommandée de déploiement national

1. Construire l'artefact depuis un commit/tag identifié.
2. Générer SHA-256 et taille.
3. Publier l'artefact sur l'hébergement HTTPS approuvé.
4. Créer le manifest en `draft`.
5. Contrôler le manifest et la signature.
6. Choisir 1 à 3 gateways canary représentatifs.
7. Passer en `canary`.
8. Attendre `installed` sur 100 % des canaries.
9. Passer à 10 %.
10. Observer santé P7, incidents et attestations.
11. Passer à 25 % puis 50 % uniquement après validation serveur.
12. Ouvrir 100 %.
13. Conserver la release précédente comme rollback jusqu'à validation nationale.

## 15. Procédure incident release

Si un gateway atteste `failed` :

1. la release est automatiquement `paused` ;
2. aucune nouvelle installation n'est proposée ;
3. analyser les logs du gateway concerné ;
4. si la version est en cause, passer la release en `rollback` ;
5. vérifier les attestations `rolled_back` ;
6. corriger le code et publier **une nouvelle release signée** ;
7. ne jamais réutiliser un binaire modifié sous le même SHA/version.

## 16. Limites restant à industrialiser

P8 sécurise la chaîne de release au niveau applicatif mais les éléments suivants restent à mettre en œuvre dans l'infrastructure nationale :

- registry/object storage officiel des artefacts ;
- pipeline reproductible de build ;
- SBOM CycloneDX/SPDX ;
- signature de provenance/SLSA ;
- scanner CVE des artefacts ;
- service systemd/OS dédié à l'updater ;
- redémarrage contrôlé et health-check post-installation ;
- fenêtres de maintenance par centre ;
- conservation/rotation des artefacts ;
- procédure formelle de rotation de la racine de signature.

Ces points constituent le chantier supply-chain/industrialisation suivant ; ils ne doivent pas être déclarés comme déjà actifs tant que l'infrastructure correspondante n'est pas déployée.
