# CodeRoute Guinée — Référentiel Media Factory nationale

## 1. Objectif

La Media Factory produit, contrôle et publie les images et vidéos utilisées dans :

- l’examen officiel du code de la route ;
- les examens blancs ;
- l’entraînement pédagogique ;
- les supports de formation des centres ;
- les démonstrations institutionnelles DNTT / Ministère.

Le principe directeur est simple : **un média d’examen est un contenu réglementé**, pas une simple illustration décorative.

Chaque média doit être traçable, juridiquement exploitable, techniquement optimisé pour les réseaux mobiles et validé avant son utilisation dans une épreuve officielle.

---

## 2. Cibles de couverture initiales

### Lot pilote premium

| Type | Cible initiale | Usage principal |
|---|---:|---|
| Photos réelles | 150+ | situations routières guinéennes |
| Illustrations contrôlées | 100+ | priorités, trajectoires, zones de conflit |
| Vidéos courtes | 30–50 | perception du risque et décisions dynamiques |
| Panneaux normalisés | catalogue complet | signalisation |
| Posters vidéo | 1 par vidéo | faible débit / aperçu |

### Répartition géographique minimale

Le premier catalogue ne doit pas représenter uniquement Conakry. Il doit progressivement couvrir :

- Conakry ;
- Kindia ;
- Mamou ;
- Labé ;
- Boké ;
- Kankan ;
- Faranah ;
- Nzérékoré ;
- routes nationales et axes interurbains ;
- zones urbaines, périurbaines et rurales.

La couverture sera pilotée par des quotas de scénarios et non uniquement par le volume total de fichiers.

---

## 3. Scénarios prioritaires à photographier / filmer

### Signalisation et intersections

- STOP ;
- cédez-le-passage ;
- priorité à droite ;
- giratoire ;
- feux tricolores ;
- ligne continue / discontinue ;
- passages piétons ;
- zones scolaires ;
- limitations de vitesse ;
- travaux et déviations.

### Situations typiques de Guinée

- taxis en arrêt ou réinsertion ;
- motos et moto-taxis ;
- marchés en bord de chaussée ;
- piétons traversant hors passage ;
- véhicules en stationnement gênant ;
- camions et véhicules lourds ;
- animaux sur chaussée ;
- chaussée dégradée ;
- nids-de-poule ;
- routes latéritiques ;
- fortes pluies ;
- eau stagnante / chaussée inondée ;
- conduite de nuit ;
- faible éclairage public ;
- dépassement sur axe interurbain ;
- véhicules d’urgence ;
- panne ou accident ;
- transport collectif ;
- approche d’école, hôpital ou marché.

---

## 4. Métadonnées obligatoires

Tout média candidat à une utilisation officielle doit posséder au minimum :

| Champ | Description |
|---|---|
| `asset_id` | identifiant immuable |
| `asset_type` | image / video / illustration / sign |
| `title` | nom métier court |
| `scenario` | scénario routier représenté |
| `country` | GN |
| `region` | région administrative |
| `prefecture` | préfecture |
| `commune` | commune si applicable |
| `road_type` | urbain / interurbain / rural / autoroute si applicable |
| `capture_date` | date de prise de vue |
| `weather` | sec / pluie / brouillard / nuit… |
| `legal_reference` | référence réglementaire associée si validée |
| `source` | équipe interne / partenaire / domaine public… |
| `license_status` | statut du droit d’utilisation |
| `consent_status` | consentement lorsque nécessaire |
| `pii_review_status` | contrôle personnes / plaques / données visibles |
| `technical_review_status` | qualité technique |
| `content_review_status` | validation pédagogique |
| `institutional_status` | draft / reviewed / approved / retired |
| `reviewed_by` | relecteur |
| `approved_by` | autorité validante |
| `checksum` | hash du fichier source |
| `version` | version du média |
| `alt_text` | description accessible |

Aucune URL seule ne doit être considérée comme preuve suffisante de gouvernance.

---

## 5. Règles techniques — images

### Source

- format de prise de vue haute résolution ;
- orientation horizontale privilégiée ;
- cible de cadrage principale : 16:9 ;
- résolution source recommandée : au moins 1920 × 1080 ;
- absence de watermark commercial ;
- pas de compression excessive avant archivage.

### Livraison web

La Media Factory doit produire des variantes adaptées :

- AVIF ;
- WebP ;
- JPEG de compatibilité ;
- largeur limitée selon le terminal ;
- qualité automatique ;
- cache CDN long pour les versions immuables.

L’original ne doit pas être envoyé systématiquement au candidat.

---

## 6. Règles techniques — vidéos

### Format pédagogique

- durée cible : 8 à 20 secondes ;
- durée maximale technique du lot initial : 30 secondes ;
- ratio 16:9 ;
- minimum recommandé : 1280 × 720 ;
- aucune séquence inutile avant la situation à analyser ;
- le candidat doit disposer d’un poster avant lecture.

### Livraison

Cibles :

- 360p pour réseaux faibles ;
- 480p pour réseau mobile standard ;
- 720p pour centres disposant d’une bonne connectivité ;
- streaming adaptatif lorsque le pipeline CDN est disponible ;
- lecture `playsInline` sur mobile ;
- préchargement `metadata`, pas téléchargement intégral automatique.

---

## 7. Protection des personnes et données visibles

Avant publication, effectuer une revue dédiée :

- visages clairement identifiables ;
- plaques d’immatriculation ;
- documents visibles ;
- écrans de téléphone ;
- enseignes contenant une donnée personnelle ;
- mineurs ;
- situations médicales / accidents sensibles.

Lorsque l’identification n’est pas indispensable à la question : anonymiser ou choisir une autre prise de vue.

Une scène ne doit jamais être mise en danger ou provoquée uniquement pour obtenir une image pédagogique.

---

## 8. Workflow de validation

```text
CAPTURE / CRÉATION
      ↓
INGESTION MEDIA FACTORY
      ↓
VALIDATION TECHNIQUE
      ↓
REVUE PII / DROITS
      ↓
REVUE PÉDAGOGIQUE
      ↓
ASSOCIATION À UNE QUESTION
      ↓
REVUE RÉGLEMENTAIRE
      ↓
APPROBATION INSTITUTIONNELLE
      ↓
PUBLICATION CDN
      ↓
UTILISATION EXAMEN
      ↓
MONITORING / RETRAIT / NOUVELLE VERSION
```

Un fichier `draft` ou `reviewed` peut être utilisé en entraînement contrôlé mais ne doit pas automatiquement devenir éligible à l’examen officiel.

---

## 9. Séparation examen officiel / entraînement

### Examen officiel

Le média doit être :

- approuvé ;
- associé à une question officiellement éligible ;
- stable pendant toute la durée d’une session ;
- traçable par identifiant/version/hash ;
- disponible hors dépendance à une URL non maîtrisée ;
- sans indice visuel révélant la bonne réponse.

### Entraînement

Le contenu peut être plus explicatif :

- annotations ;
- flèches ;
- mise en évidence des trajectoires ;
- correction visuelle ;
- explications après réponse ;
- variantes pédagogiques.

Les versions annotées ne doivent jamais être réutilisées par erreur dans une épreuve officielle.

---

## 10. Contrôle qualité avant publication

Checklist minimale :

- [ ] scène conforme à la question ;
- [ ] aucune ambiguïté visuelle critique ;
- [ ] aucune bonne réponse révélée par une annotation ;
- [ ] cadrage lisible sur téléphone ;
- [ ] ALT renseigné ;
- [ ] HTTPS ;
- [ ] source/licence documentée ;
- [ ] contrôle PII effectué ;
- [ ] résolution suffisante ;
- [ ] poids optimisé ;
- [ ] poster présent pour vidéo ;
- [ ] lecture testée en faible débit ;
- [ ] version et checksum enregistrés ;
- [ ] validation pédagogique ;
- [ ] validation institutionnelle si média officiel.

---

## 11. KPIs de pilotage

Le tableau de bord Media Factory doit suivre :

- % de questions avec média ;
- % de questions approuvées avec média ;
- nombre d’images ;
- nombre de vidéos ;
- ALT manquants ;
- URLs non sécurisées héritées ;
- répartition par région ;
- répartition par scénario ;
- taux de média validé / rejeté ;
- temps moyen de validation ;
- taux d’échec de chargement candidat ;
- poids moyen image / vidéo ;
- consommation réseau moyenne par examen ;
- couverture faible débit.

Le endpoint `GET /api/v1/questions/media-coverage` constitue le premier niveau technique de ce tableau de bord.

---

## 12. Critères de passage à l’échelle nationale

Avant généralisation :

1. catalogue officiel identifié et versionné ;
2. droits d’utilisation vérifiés ;
3. workflow d’approbation opérationnel ;
4. couverture représentative de plusieurs régions ;
5. tests réseau 3G / Edge / coupure ;
6. médias préchargés ou mis en cache dans les centres critiques ;
7. CDN et transformations automatiques opérationnels ;
8. monitoring des erreurs de chargement ;
9. procédure de retrait immédiat d’un média erroné ;
10. preuve d’intégrité permettant de savoir quelle version a été présentée lors d’une tentative.

---

## 13. Étapes d’implémentation restantes

### P1 — Fondation — en cours

- policy upload ;
- URLs sûres ;
- Cloudinary signé ;
- couverture média ;
- variables Render.

### P2 — Frontend admin

- validation taille / MIME avant transfert ;
- contrôle durée vidéo ;
- aperçu avant publication ;
- état upload / erreur ;
- affichage des règles de policy.

### P3 — Delivery candidat

- média 16:9 ;
- poster vidéo ;
- loading / error states ;
- fullscreen ;
- variantes responsive ;
- livraison adaptative vidéo.

### P4 — Gouvernance nationale

- catalogue et métadonnées complètes ;
- workflow de revue ;
- quotas régionaux ;
- versioning et checksums ;
- audit institutionnel.

### P5 — Résilience centres

- pré-cache des médias de session ;
- packages signés ;
- fonctionnement réseau intermittent ;
- reprise sans altération du contenu présenté.
