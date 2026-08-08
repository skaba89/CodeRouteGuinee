# CodeRoute Center Edge Agent v1

Daemon local sécurisé pour assurer la continuité d'un examen officiel pendant une panne WAN du centre.

## Garanties

- aucune banque officielle globale dans le centre ;
- aucune `correct_answer` / explication dans le lease ;
- scoring final uniquement sur la plateforme centrale ;
- lease central Ed25519 conservé inchangé ;
- projection média LAN séparée du paquet signé ;
- SQLite WAL avec payloads sensibles chiffrés AES-256-GCM ;
- journal de réponses append-only/hash-chaîné ;
- chronométrage local basé sur `time.monotonic()` ;
- reboot d'un lease actif => `EDGE_REVALIDATION_REQUIRED` ;
- cache média préchargé et vérifié SHA-256 ;
- HTTPS LAN obligatoire par défaut ;
- CORS explicite, jamais `*` ;
- token opérateur séparé du token candidat ;
- session candidat liée à l'identifiant persistant du poste.

## Architecture

```text
Postes candidats / VLAN EXAM
          |
        HTTPS
          |
   Center Edge Agent
   FastAPI + SQLite + AES-GCM
   journal + cache média SHA256
          |
       WAN HTTPS
          |
 CodeRoute national / central
```

## Pré-requis

1. gateway enrôlé via la fondation Center Edge (#110) ;
2. Offline Lease v1 disponible (#111) ;
3. identité Ed25519 locale :

```bash
python scripts/generate_edge_identity.py --label "Gateway Edge Ratoma"
```

4. certificat TLS LAN émis par une CA approuvée sur les postes du centre ;
5. machine dédiée + stockage persistant + UPS ;
6. VLAN EXAM isolé.

## Variables principales

```text
CODEROUTE_EDGE_CENTRAL_URL=https://coderouteguinee-backend.onrender.com
CODEROUTE_EDGE_NODE_ID=<uuid>
CODEROUTE_EDGE_CENTER_ID=<uuid>
CODEROUTE_EDGE_PRIVATE_KEY_PATH=/var/lib/coderoute-edge/private-key.pem
CODEROUTE_EDGE_DB_PATH=/var/lib/coderoute-edge/edge.db
CODEROUTE_EDGE_STORAGE_KEY_PATH=/var/lib/coderoute-edge/storage.key
CODEROUTE_EDGE_MEDIA_DIR=/var/lib/coderoute-edge/media
CODEROUTE_EDGE_OPERATOR_TOKEN=<secret aléatoire 32+ caractères>
CODEROUTE_EDGE_ALLOWED_ORIGINS=https://coderouteguinee-frontend.onrender.com
CODEROUTE_EDGE_TLS_CERT_PATH=/var/lib/coderoute-edge/tls/edge.crt
CODEROUTE_EDGE_TLS_KEY_PATH=/var/lib/coderoute-edge/tls/edge.key
CODEROUTE_EDGE_BIND_HOST=0.0.0.0
CODEROUTE_EDGE_BIND_PORT=8443
```

`CODEROUTE_EDGE_ALLOW_INSECURE_HTTP=true` est réservé au laboratoire/CI.

## Docker

```bash
docker build -t coderoute-edge:0.1.0 edge_agent/

docker run --restart unless-stopped \
  --read-only \
  --tmpfs /tmp:rw,noexec,nosuid,size=64m \
  -p 8443:8443 \
  -v /srv/coderoute-edge:/var/lib/coderoute-edge \
  --env-file /srv/coderoute-edge/edge.env \
  coderoute-edge:0.1.0
```

La clé privée, `storage.key`, la DB locale et les certificats restent dans le volume du centre et ne doivent jamais être envoyés dans Git ou Render.

## Parcours opérateur

### Santé

```http
GET /health
```

### Heartbeat

```http
POST /operator/heartbeat
X-Edge-Operator-Token: <secret opérateur>
```

### Activation offline d'une tentative

Après paiement, check-in et démarrage central :

```http
POST /operator/leases
X-Edge-Operator-Token: <secret opérateur>

{
  "attempt_id": "...",
  "station_device_key": "CRG-STATION-...",
  "lang": "fr"
}
```

L'agent :

1. envoie un heartbeat ;
2. demande le lease au central ;
3. vérifie la signature Ed25519 centrale ;
4. télécharge tous les médias requis en streaming ;
5. vérifie MIME, taille et SHA-256 ;
6. chiffre le bundle dans SQLite ;
7. génère un `access_token` local lié au poste.

Si un média requis manque, l'activation échoue : pas de mode offline partiel.

## API candidat

Les appels JSON utilisent :

```text
X-Edge-Access-Token: <token session>
X-CodeRoute-Station-Key: <device_key du poste>
```

### Charger l'examen

```http
GET /v1/exams/{attempt_id}
```

### Enregistrer une réponse

```http
POST /v1/exams/{attempt_id}/answers
{
  "question_id": "...",
  "answer": "..."
}
```

### Finaliser localement

```http
POST /v1/exams/{attempt_id}/finalize
```

Aucun score n'est retourné localement.

## Médias compatibles `<img>` / `<video>`

Les balises HTML natives ne peuvent pas joindre les headers candidats. L'agent fournit donc, uniquement dans la réponse authentifiée de l'examen, des URLs de la forme :

```text
/v1/exams/{attempt_id}/media/{sha256}?ticket=<HMAC>
```

Le ticket :

- est calculé avec `storage.key` ;
- est lié à `attempt_id + digest` ;
- n'autorise aucun autre média ;
- n'est jamais présent dans le lease central signé.

Le serveur local vérifie le ticket puis recalcule le SHA-256 du fichier avant de le servir.

## Retour du WAN

```http
POST /operator/sync/{attempt_id}
X-Edge-Operator-Token: <secret opérateur>
```

Le daemon :

1. rétablit le heartbeat ;
2. déchiffre le journal ;
3. signe la preuve de synchronisation ;
4. transmet le journal au central ;
5. marque le lease `synced` si le central l'accepte.

Le central recalcule le résultat avec la clé de correction officielle.

## Reboot pendant la panne

L'origine temporelle d'une tentative active est monotone et volontairement non reconstruite avec l'horloge murale après reboot.

- lease finalisé : sync possible après reboot ;
- lease actif : `EDGE_REVALIDATION_REQUIRED` ;
- le WAN doit être rétabli pour revalider avant poursuite.

Ce comportement fail-closed empêche de gagner du temps d'examen en modifiant l'heure du système.

## Durcissement centre recommandé

- Secure Boot + chiffrement disque ;
- compte OS non privilégié ;
- firewall entrant : VLAN EXAM uniquement ;
- firewall sortant : API centrale + CDN autorisés ;
- CA TLS de centre/DNTT ;
- UPS gateway + switch + routeur ;
- rotation du token opérateur ;
- révocation du nœud en cas de vol ;
- exercice WAN-off avant campagne nationale.

## Prochains lots

1. intégration automatique du frontend candidat Central ↔ Edge ;
2. liaison du lease au `CenterStation` central ;
3. UI opérateur santé/cache/sync ;
4. synchronisation automatique avec backoff ;
5. quota/LRU média multi-session ;
6. attestation TPM et double gateway pour grands centres.
