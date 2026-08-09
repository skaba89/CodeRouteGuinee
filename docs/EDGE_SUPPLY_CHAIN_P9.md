# P9 — Supply chain logicielle et exploitation système Center Edge

## 1. Objectif

P9 transforme le mécanisme applicatif P8 de release signée en chaîne de livraison exploitable à l'échelle nationale.

Le principe est fail-closed : une release ne peut pas atteindre un canary simplement parce qu'un fichier tar.gz existe et que son SHA-256 est connu. Elle doit disposer d'une provenance CI, d'un SBOM, d'un audit de dépendances réussi, d'un manifeste re-signé par la DNTT, d'un permis d'installation récent lié au gateway et d'une transaction système locale sûre.

P9 ne modifie ni le moteur de score, ni la banque officielle, ni la logique de correction candidat.

## 2. Version et capacités

Version cible : `edge-agent-0.4.0`.

Capacités nationales attendues :

- `answer-journal-v1` ;
- `exam-lease-v1` ;
- `fleet-telemetry-v1` ;
- `maintenance-updater-v1` ;
- `media-prefetch-v1` ;
- `operator-status-v1` ;
- `release-attestation-v1` ;
- `release-key-rotation-v1` ;
- `release-staging-v1` ;
- `supply-chain-evidence-v1`.

Un gateway sans ces capacités apparaît en dérive dans la supervision nationale.

## 3. Modèle de menace

P9 distingue quatre niveaux de confiance.

### 3.1 Control plane DNTT

Le central :

- crée le draft ;
- rattache la preuve CI ;
- re-signe le manifeste ;
- décide canary/rolling/released/pause/rollback/revoked ;
- émet un permis d'installation court, signé et lié à un gateway précis.

### 3.2 Daemon Edge non privilégié

Le daemon :

- dialogue avec le central avec l'identité Ed25519 du gateway ;
- télécharge l'artefact ;
- vérifie signature, URL, taille et SHA ;
- écrit uniquement dans `/var/lib/coderoute-edge/release-staging` en production ;
- ne peut pas modifier `/opt/coderoute-edge/releases` ;
- ne possède ni Docker socket ni endpoint HTTP permettant d'installer du code.

La compromission du daemon ne doit donc pas suffire à remplacer l'exécutable actif.

### 3.3 Updater root

Le root updater :

- ne fait pas confiance au champ `verified=true` écrit par le daemon ;
- recharge un trust store public root-owned ;
- re-vérifie la signature Ed25519 du manifeste ;
- re-vérifie la supply chain ;
- re-vérifie un permis d'installation central fraîchement renouvelé ;
- re-hashe l'artefact ;
- copie vers un workspace root-owned ;
- extrait avec les gardes P8 ;
- construit le runtime offline ;
- redémarre systemd ;
- valide `/health` et la version exacte ;
- rollback automatiquement si la nouvelle version ne confirme pas sa santé.

### 3.4 Poste candidat

Le poste candidat n'a aucun rôle dans la supply chain et ne reçoit aucun secret de release.

## 4. Preuve CI obligatoire avant canary

Le workflow `.github/workflows/edge-release-supply-chain.yml` produit :

- l'artefact `edge-agent-X.Y.Z.tar.gz` ;
- son SHA-256 et sa taille ;
- le `requirements.runtime.lock` ;
- `dependency-audit.json` ;
- `edge-runtime.sbom.cdx.json` ;
- une attestation GitHub de provenance de build ;
- une attestation GitHub du SBOM ;
- `control-plane-evidence.json`.

Exemple de preuve attendue :

```json
{
  "builder": "github-actions",
  "source_commit_sha": "...",
  "workflow_ref": "Edge Release Supply Chain@refs/tags/edge-agent-0.4.0",
  "provenance_url": "https://github.com/.../attestations/...",
  "sbom_sha256": "...",
  "sbom_attestation_url": "https://github.com/.../attestations/...",
  "subject_sha256": "...",
  "vulnerability_scan_status": "passed"
}
```

Le backend impose :

- `subject_sha256 == manifest.artifact.sha256` ;
- SHA SBOM valide ;
- commit source hexadécimal valide ;
- URLs de provenance publiques en HTTPS ;
- `vulnerability_scan_status == passed` pour autoriser une promotion.

Une preuve `failed` peut être conservée pour audit, mais `supply_chain_ready=false` et le rollout reste bloqué.

## 5. Workflow de build P9

Ordre :

1. checkout par action pinnée sur SHA ;
2. Python 3.12 ;
3. validation stricte de `edge-agent-X.Y.Z` ;
4. compilation du package et des scripts privilégiés ;
5. exécution des tests Edge ;
6. téléchargement d'un wheelhouse binaire depuis `requirements.runtime.txt` ;
7. génération de `requirements.runtime.lock` à partir des métadonnées et SHA-256 réels des wheels ;
8. installation de preuve sans Internet avec `--no-index --require-hashes` ;
9. audit `pip-audit` ;
10. génération CycloneDX ;
11. construction déterministe du tar.gz ;
12. attestation de provenance ;
13. attestation SBOM ;
14. génération du bundle de preuve DNTT ;
15. upload des preuves ;
16. échec final si le scan/audit n'est pas vert.

Les actions GitHub utilisées dans ce workflow sont pinnées sur des SHA de commit complets afin de limiter le risque de déplacement d'un tag d'action.

## 6. Runtime autonome hors Internet

Le runtime publié n'effectue pas de `pip install` sur Internet dans un centre.

Le tar.gz contient :

- `edge_agent/coderoute_edge` ;
- `requirements.runtime.txt` ;
- `requirements.runtime.lock` ;
- `wheelhouse/*.whl` ;
- les scripts d'updater.

Après extraction, l'updater root crée :

```text
/opt/coderoute-edge/releases/versions/<version>/.venv
```

puis exécute conceptuellement :

```bash
pip install \
  --no-index \
  --find-links wheelhouse \
  --require-hashes \
  -r requirements.runtime.lock
```

Le SHA du lock est conservé dans `.runtime-ready.json`. Une modification du lock force la reconstruction du venv.

## 7. Séparation staging / code exécutable

Production :

```text
/var/lib/coderoute-edge/release-staging   # daemon coderoute-edge : RW
/opt/coderoute-edge/releases              # root : RW ; daemon : RO
```

Le daemon ne doit jamais être propriétaire du répertoire des versions exécutables.

Le daemon télécharge :

```text
/var/lib/coderoute-edge/release-staging/<release_id>.tar.gz
/var/lib/coderoute-edge/release-staging/staged.json
```

L'updater root re-vérifie puis copie vers :

```text
/opt/coderoute-edge/releases/<release_id>.tar.gz
```

avant d'appeler le mécanisme P8 d'extraction/versionnement.

## 8. Trust store root-owned

Fichier production :

```text
/etc/coderoute-edge/release-trust.json
```

Le fichier ne contient que des clés publiques.

Exemple :

```json
{
  "trusted_keys": [
    {
      "key_id": "edge-release-v1:<fingerprint>",
      "public_key_b64": "...",
      "active": true
    }
  ]
}
```

Exigences :

- propriétaire root ;
- non writable par groupe/autres ;
- provisionné hors bande ;
- fingerprint vérifié par procédure DNTT ;
- jamais remplacé automatiquement par une clé récupérée du réseau sans validation institutionnelle.

## 9. Rotation des clés de signature

Variables central :

```text
EDGE_RELEASE_SIGNING_SECRET=<secret actif>
EDGE_RELEASE_PREVIOUS_SIGNING_SECRETS=<secret précédent 1>,<secret précédent 2>
```

Procédure :

1. générer un nouveau secret hors du dépôt ;
2. conserver l'ancien secret dans `EDGE_RELEASE_PREVIOUS_SIGNING_SECRETS` ;
3. déployer le central ;
4. récupérer les nouvelles clés publiques/fingerprints via le point de contrôle DNTT ;
5. distribuer hors bande un trust store contenant nouvelle + ancienne clé ;
6. vérifier que la flotte annonce la capacité `release-key-rotation-v1` ;
7. lancer une release signée par la nouvelle clé ;
8. attendre la conformité nationale ;
9. ne retirer l'ancienne clé du trust store qu'après expiration de tous les artefacts/rollbacks qui en dépendent ;
10. retirer ensuite l'ancien secret côté central.

Ne jamais retirer d'abord l'ancienne clé des centres : cela rendrait les rollbacks historiques impossibles.

## 10. Permis d'installation court

Une signature de manifeste prouve l'intégrité d'une release, mais elle ne prouve pas qu'elle est encore autorisée à l'instant T.

P9 ajoute `center_edge_install_authorization_v1`.

Le central signe :

- release cible ;
- release source pour un rollback ;
- `node_id` ;
- `center_id` ;
- action ;
- version courante ;
- version cible ;
- SHA artefact ;
- `issued_at` ;
- `expires_at`.

TTL par défaut : 20 minutes, borné entre 5 et 60 minutes.

Juste avant une transaction, `run_system_update.py` appelle localement :

```text
POST /operator/release/check
```

Le daemon relaie un nouveau check signé au central.

Cas fail-closed :

- release mise en pause : pas de nouveau permis ;
- release révoquée : pas de nouveau permis ;
- gateway sorti de la cohorte : pas de nouveau permis ;
- autre release devenue prioritaire : le staging actuel n'est pas appliqué ;
- central/WAN indisponible : pas d'installation ;
- permis expiré : root refuse ;
- permis d'un autre gateway : root refuse.

Un fichier peut donc rester préchargé sans devenir exécutable.

## 11. Fenêtres de maintenance

Configuration :

```text
CODEROUTE_EDGE_MAINTENANCE_WINDOWS=sun@01:00-04:00
CODEROUTE_EDGE_MAINTENANCE_TIMEZONE=Africa/Conakry
```

Plusieurs fenêtres :

```text
sun@01:00-04:00;wed@01:00-03:00
```

Fenêtre traversant minuit :

```text
daily@23:00-00:30
```

Un `--emergency-window-bypass` existe pour une intervention institutionnelle, mais il contourne uniquement l'horaire.

Il ne contourne jamais la sécurité des examens.

## 12. Quiescence obligatoire

Avant tout changement de version, l'updater lit la base locale SQLite en read-only.

Installation interdite si :

- au moins un lease `active` ;
- au moins un lease `finalized` non synchronisé ;
- un état de lease inconnu est présent.

Seuls les leases `synced` sont compatibles avec une maintenance.

Objectif : aucun restart pendant un examen officiel et aucune perte d'un journal finalisé en attente de centralisation.

## 13. Transaction système

Séquence :

```text
fenêtre maintenance
  -> quiescence
  -> re-check central
  -> permis court signé
  -> trust store root
  -> signature manifest
  -> preuve supply chain
  -> SHA/taille
  -> copie staging -> root workspace
  -> extraction P8 sécurisée
  -> runtime offline hash-locké
  -> switch current
  -> systemd restart
  -> /health
  -> comparaison exacte software_version
```

Si la version attendue répond correctement : transaction confirmée.

Sinon :

```text
switch previous
  -> systemd restart
  -> /health
  -> validation version précédente
  -> reçu failed pour la release fautive
```

Le reçu `failed` permet au central de déclencher la pause automatique P8/P9.

## 14. Attestation après redémarrage

Le root updater dépose le reçu dans le staging non privilégié.

Au prochain heartbeat du daemon :

- si le reçu est `installed`, le daemon doit réellement annoncer la même version ;
- si le reçu est `rolled_back`, même règle ;
- un reçu `failed` peut être attesté pour provoquer la pause du rollout ;
- si le central est indisponible, le reçu reste présent et sera retenté plus tard.

Une simple copie de fichiers n'est donc jamais comptée comme installation nationale réussie.

## 15. Units systemd

Fichiers :

```text
edge_agent/deploy/systemd/coderoute-edge.service
edge_agent/deploy/systemd/coderoute-edge-updater.service
edge_agent/deploy/systemd/coderoute-edge-updater.timer
```

Le daemon :

- tourne comme `coderoute-edge` ;
- n'écrit pas dans `/opt/coderoute-edge/releases` ;
- n'a pas de capacités ambiantes ;
- utilise `ProtectSystem=strict`, `PrivateDevices`, `NoNewPrivileges`, etc.

L'updater :

- est `root` ;
- est `oneshot` ;
- n'exécute aucun `/bin/sh` reçu du réseau ;
- ne possède pas de Docker socket ;
- écrit uniquement dans le staging et l'arbre des releases ;
- utilise le Python du runtime actif vérifié.

Le timer :

- démarre après 10 minutes ;
- vérifie toutes les 15 minutes ;
- ajoute jusqu'à 2 minutes de jitter ;
- est persistent.

Le timer ne signifie pas « installer toutes les 15 minutes ». Il signifie « vérifier si une transaction autorisée, dans la fenêtre et quiescente, est possible ».

## 16. Bootstrap P8 -> P9

P9 introduit une frontière de privilège que P8 ne pouvait pas s'auto-installer rétroactivement.

Le premier passage d'un gateway P8 à P9 doit donc être une opération de bootstrap contrôlée sur les gateways canary.

Ordre recommandé :

1. produire `edge-agent-0.4.0` via le workflow P9 ;
2. conserver le bundle de preuves ;
3. créer le draft central avec URL/SHA/taille ;
4. rattacher `control-plane-evidence.json` ;
5. re-signer le manifeste ;
6. sélectionner quelques gateways pilotes ;
7. provisionner hors bande `/etc/coderoute-edge/release-trust.json` ;
8. vérifier manuellement le fingerprint de la clé DNTT ;
9. préparer le premier artefact P9 et son `.venv` sous `/opt/coderoute-edge/releases` avec les hashes du bundle ;
10. installer les units avec `install-systemd.sh` ;
11. vérifier TLS, DB, storage key et identité gateway ;
12. démarrer le service ;
13. vérifier `/health` = `edge-agent-0.4.0` ;
14. activer le timer ;
15. observer le canary avant extension.

Après cette migration initiale, les versions P9 suivantes utilisent la chaîne transactionnelle automatique.

Ne pas tenter de déployer les units sur l'ensemble du pays avant validation d'un petit lot de gateways physiques.

## 17. Incident : nouvelle version défaillante

Automatique :

1. le health-check échoue ou retourne une mauvaise version ;
2. rollback local vers `previous` ;
3. restart ;
4. validation de la version précédente ;
5. reçu `failed` ;
6. attestation au central ;
7. release mise en pause automatiquement.

DNTT :

- ne pas reprendre le rollout sans analyse ;
- conserver SBOM, provenance, audit, logs systemd et manifest ;
- identifier le commit source ;
- corriger dans une nouvelle version ;
- reconstruire par la CI ;
- ne jamais remplacer silencieusement un tar.gz sous le même SHA/version.

## 18. Incident : compromission supposée de clé release

1. pause de toutes les releases actives ;
2. générer un nouveau secret de signature hors bande ;
3. ajouter temporairement ancienne + nouvelle clé au trust store si l'ancienne n'est pas confirmée compromise ;
4. si compromission confirmée, retirer l'ancienne clé des trust stores par canal d'administration contrôlé ;
5. révoquer les releases signées par la clé compromise selon l'analyse d'incident ;
6. reconstruire/re-signer une version saine ;
7. reprendre sur canary seulement.

En cas de compromission confirmée, la continuité de rollback doit être arbitrée contre le risque de continuer à faire confiance à l'ancienne clé.

## 19. Ce que P9 ne prétend pas résoudre

P9 améliore fortement la chaîne de livraison mais ne remplace pas :

- un HSM/KMS gouvernemental pour la racine de signature ;
- une PKI de postes/gateways avec rotation automatisée des certificats LAN ;
- un dépôt d'artefacts souverain haute disponibilité ;
- une politique CVE institutionnelle avec SLA de remédiation par criticité ;
- une collecte SIEM nationale des événements systemd/host ;
- une gestion MDM/OS complète des gateways ;
- le secure boot/TPM des machines physiques.

Ces éléments constituent les chantiers infrastructure/sécurité ultérieurs.

## 20. Limite architecture actuelle du wheelhouse

Le workflow courant construit le wheelhouse sur `ubuntu-latest` x86_64.

Il est donc adapté aux gateways Linux x86_64 compatibles avec ce runtime.

Avant introduction de gateways ARM64 :

- ajouter une matrice de build par architecture ;
- produire un artefact/manifeste distinct par architecture ;
- inclure l'architecture dans le manifeste signé ;
- empêcher un gateway d'installer un artefact d'une architecture différente.

Ne pas considérer P9 actuel comme multi-architecture.

## 21. Recette nationale minimale

Avant passage canary :

- CI complète terminée ;
- scan `passed` ;
- provenance accessible ;
- SBOM accessible ;
- SHA bundle CI = SHA draft ;
- manifeste re-signé ;
- trust store du canary vérifié ;
- gateway online/sain ;
- aucune tentative active ;
- aucun journal finalisé non synchronisé ;
- fenêtre de maintenance définie ;
- version précédente rollbackable.

Après installation canary :

- `/health` exact ;
- heartbeat 0.4.0 ;
- attestation `installed` ;
- zéro corruption locale ;
- zéro revalidation inattendue ;
- synchronisation examen fonctionnelle ;
- redémarrage physique de test ;
- test offline/retour WAN ;
- test rollback volontaire sur environnement de recette.

## 22. Règle de décision DNTT

Une release logicielle n'est pas un simple fichier à distribuer.

Pour P9, une release est déployable uniquement lorsque les preuves suivantes sont toutes cohérentes :

```text
commit source
  == provenance CI
  == SBOM/audit
  == artefact SHA
  == manifeste DNTT signé
  == permis gateway récent
  == artefact re-vérifié root
  == runtime offline hash-locké
  == version réellement démarrée
  == attestation centrale
```

Une rupture dans cette chaîne doit bloquer la promotion, jamais être transformée en avertissement ignoré.
