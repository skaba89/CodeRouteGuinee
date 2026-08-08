# Center Edge — Console d'exploitation centre (P6)

## Objectif

La console `#/center-edge` permet au responsable d'un centre d'examen de piloter le gateway local même lorsque la liaison WAN vers la DNTT est indisponible.

Elle ne remplace pas l'administration nationale et ne calcule aucun résultat. Elle sert uniquement à :

- vérifier que le gateway LAN répond ;
- tester la liaison centrale via un heartbeat signé ;
- visualiser l'état des tentatives déjà présentes sur le gateway ;
- préparer un lease Edge pour une tentative officielle déjà ouverte et un poste enregistré ;
- transmettre au poste candidat le lien de claim temporaire ;
- identifier les journaux finalisés en attente ;
- relancer la synchronisation après retour du WAN ;
- détecter une tentative active qui exige une revalidation après redémarrage du gateway.

## Accès opérateur

Le navigateur se connecte directement au gateway avec :

- l'URL HTTPS LAN, par exemple `https://edge-ratoma.coderoute.local:8443` ;
- `X-Edge-Operator-Token`.

L'URL du gateway peut être mémorisée localement. Le secret opérateur est conservé uniquement dans `sessionStorage` et disparaît à la fermeture de l'onglet.

Le mode HTTP n'est accepté par le client que pour `localhost` / `127.0.0.1` en laboratoire.

## Vue opérateur du gateway

`GET /operator/status` est protégé par le token opérateur. Il retourne uniquement des métadonnées d'exploitation filtrées :

- ID tentative / lease ;
- état local ;
- deadline ;
- poste signé (device key, label, salle) ;
- nombre de questions ;
- nombre d'événements dans le journal ;
- état du claim ;
- synchronisation en attente ;
- revalidation requise ;
- volumétrie du cache média.

Ne sont jamais exposés dans cette réponse : texte/options des questions, réponses candidat, claim brut, token candidat, hash du poste, ciphertext, journal détaillé ou clé de correction.

`GET /health` reste public et minimal : il ne contient pas la liste des tentatives.

## Préparation d'une tentative Edge

L'opérateur fournit :

1. l'`attempt_id` d'une tentative officielle déjà ouverte ;
2. le `device_key` du poste candidat enregistré.

Le gateway appelle le central, vérifie le lease signé, vérifie le binding du poste, précharge les médias et retourne une URL candidat temporaire.

La console ne persiste jamais le `claim_token` brut. Elle conserve seulement l'URL candidat en mémoire React le temps de sa validité.

## Synchronisation

Une tentative finalisée localement apparaît `À synchroniser`. L'opérateur peut :

- synchroniser une tentative ;
- synchroniser toutes les tentatives finalisées.

Le gateway envoie le journal signé au central. Le scoring reste exclusivement côté DNTT.

## Reboot du gateway

L'horloge d'examen locale utilise une origine monotone en mémoire. Si le gateway redémarre alors qu'une tentative est active, la console affiche `Revalidation requise`. Le système ne reconstitue pas arbitrairement le temps à partir de l'horloge murale.

## Recette minimale centre

1. Connecter la console au gateway.
2. Vérifier `Gateway local = EN LIGNE`.
3. Lancer `Tester la liaison DNTT` avec WAN disponible.
4. Ouvrir une tentative officielle et lier le poste CenterStation.
5. Précharger/activer Edge.
6. Ouvrir le lien sur le poste correspondant.
7. Couper le WAN après chargement.
8. Répondre puis finaliser l'examen.
9. Vérifier `À synchroniser = 1` dans la console.
10. Rétablir le WAN puis synchroniser.
11. Vérifier que le résultat apparaît uniquement depuis le central.

## Suite P7

Le prochain niveau est la supervision nationale des gateways : inventaire des nœuds par centre, dernière présence, version logicielle, dérive de configuration, files de synchronisation, incidents et déploiement progressif des versions Edge.
