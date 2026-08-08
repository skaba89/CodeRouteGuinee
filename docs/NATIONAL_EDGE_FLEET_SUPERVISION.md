# P7 — Supervision nationale de la flotte Center Edge

## Objectif

P7 donne à la DNTT une vision nationale de la capacité réelle des centres à continuer les examens CodeRoute en mode Edge lorsque la connectivité WAN est instable ou indisponible.

La supervision ne collecte aucune réponse candidat, aucune question, aucun token et aucun journal détaillé. Elle ne remplace pas les preuves d'audit : elle transmet uniquement des compteurs d'exploitation signés par le gateway.

## Chaîne de confiance

Chaque gateway possède déjà une identité Ed25519 enrôlée auprès de la DNTT. P7 étend le heartbeat existant avec une télémétrie agrégée :

- leases actifs ;
- leases finalisés ;
- leases déjà synchronisés ;
- journaux finalisés en attente de synchronisation ;
- tentatives nécessitant une revalidation après reboot ;
- leases locaux illisibles/corrompus ;
- nombre de fichiers du cache média ;
- volume du cache média.

Ces valeurs font partie du payload canonique signé. Modifier un compteur après signature invalide donc le heartbeat.

## Confidentialité

Le heartbeat national interdit volontairement :

- `attempt_id` ;
- `candidate_id` ;
- identité candidat ;
- numéro ou contenu des questions ;
- réponses ;
- `device_key` du poste candidat ;
- événements du journal ;
- tokens d'accès ou de claim ;
- ciphertext du store Edge.

La vue nationale expose le fingerprint de la clé publique mais jamais la clé privée ni le `public_key_b64` complet.

## Version P7

La version de référence est :

`edge-agent-0.2.0`

Le central utilise `CODEROUTE_EDGE_TARGET_VERSION` pour définir la version cible nationale. Sans variable explicite, la cible P7 est `edge-agent-0.2.0`.

Capacités obligatoires P7 :

- `answer-journal-v1` ;
- `exam-lease-v1` ;
- `fleet-telemetry-v1` ;
- `media-prefetch-v1` ;
- `operator-status-v1`.

Un agent 0.1.x continue à transmettre ses anciens heartbeats. Il n'est pas brutalement rejeté : la DNTT le classe en dérive de version/capacités et le place dans la vague de mise à niveau.

## Score de santé d'un gateway

Chaque nœud reçoit un score de 0 à 100. Les pénalités sont explicables par des alertes :

- gateway actif mais hors ligne : critique ;
- identité suspendue ou révoquée : critique ;
- version différente de la cible : avertissement ;
- capacité obligatoire absente : avertissement ;
- télémétrie P7 absente : avertissement ;
- backlog de synchronisation : avertissement puis critique à partir d'un volume important ;
- revalidation après reboot : critique ;
- corruption locale : critique ;
- dérive d'horloge significative : avertissement ou critique.

Interprétation :

- 85–100 : `healthy` ;
- 60–84 : `degraded` ;
- 0–59 : `critical`.

Le score est une aide opérationnelle. Il ne décide jamais du résultat d'un candidat.

## Santé d'un centre

Le central agrège tous les gateways d'un centre actif/accrédité. Un centre sans gateway est critique pour la continuité Edge. Sont suivis :

- nombre de gateways ;
- gateways en ligne ;
- score moyen ;
- backlog de synchronisation ;
- revalidations ;
- corruptions ;
- nœuds en dérive de version ;
- alertes prioritaires.

## Vue nationale DNTT

Endpoint :

`GET /api/v1/center-edge/fleet`

Accès : `admin` et `super_admin`.

La réponse contient :

- état national ;
- version cible ;
- capacités obligatoires ;
- synthèse des centres ;
- synthèse des nœuds ;
- backlog national ;
- incidents Edge techniques ;
- état de rollout ;
- détail par centre ;
- détail par gateway.

Le dashboard d'administration CodeRoute intègre cette vue sous « Flotte Center Edge — continuité nationale » et l'actualise toutes les 30 secondes.

## Rollout national

P7 prépare le rollout sans déployer arbitrairement un exécutable à distance.

Les nœuds sont classés :

- **conforme** : version cible + capacités requises ;
- **mise à niveau requise** : version ou capacités en dérive ;
- **bloqué** : nœud suspendu/révoqué ou santé critique.

Ordre recommandé :

1. laboratoire DNTT ;
2. centre pilote Conakry ;
3. 5–10 centres représentatifs des différentes conditions réseau ;
4. vague régionale ;
5. généralisation nationale.

Une mise à jour OTA distante devra faire l'objet d'un chantier séparé avec manifeste signé, hash du binaire, canal de release, rollback, fenêtres de maintenance et preuve d'installation.

## Alertes opérationnelles prioritaires

### EDGE_OFFLINE

Aucun heartbeat récent. Vérifier alimentation, LAN, WAN et service Edge.

### EDGE_SYNC_BACKLOG

Des examens sont finalisés mais pas encore intégrés au central. Le résultat candidat doit rester en attente tant que la synchronisation n'est pas acceptée.

### EDGE_REVALIDATION_REQUIRED

Le gateway a redémarré alors qu'une tentative était active. Ne jamais reconstruire arbitrairement l'horloge ; passer par le mécanisme de revalidation prévu.

### EDGE_LOCAL_CORRUPTION

Un lease local est illisible. Il reste isolé et ne doit pas bloquer les autres tentatives. Ouvrir un incident technique et conserver les preuves locales avant toute intervention destructive.

### EDGE_VERSION_DRIFT / EDGE_CAPABILITY_DRIFT

Le nœud n'est pas au standard national courant. Planifier sa mise à niveau avant une session critique.

## Recette P7

1. Enrôler un gateway.
2. Démarrer l'agent 0.2.0.
3. Vérifier que le heartbeat contient la télémétrie signée.
4. Vérifier `/center-edge/fleet` côté DNTT.
5. Créer/finaliser une tentative Edge sans synchronisation et constater l'augmentation de `sync_pending`.
6. Redémarrer un gateway pendant une tentative active et constater `revalidation_required`.
7. Simuler un nœud 0.1.0 et vérifier la dérive de version/capacités.
8. Vérifier qu'une modification de la télémétrie après signature est rejetée en 401.
9. Vérifier qu'aucune donnée candidat/question/réponse n'est présente dans la télémétrie ou la vue nationale.
10. Rétablir le WAN et vérifier la diminution du backlog après synchronisation acceptée.

## Suite recommandée — P8

P8 pourra couvrir le **Release Management Edge sécurisé** : artefacts signés, canary, vagues de déploiement, rollback, attestations d'installation et politique de maintenance nationale.
