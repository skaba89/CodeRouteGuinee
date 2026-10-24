# Démonstration DNTT — script de 15 minutes

Démonstration de CodeRoute Guinée devant la Direction Nationale des Transports
Terrestres : parcours complet d'un candidat, supervision territoriale et
journal d'audit infalsifiable.

> **À dire dès l'ouverture, et à respecter pendant toute la démonstration :**
> les données sont **fictives** (≈ 2 600 candidats générés sur 135 centres),
> les paiements sont **simulés** (mode sandbox, aucun débit réel), et la banque
> de questions est une **banque de démonstration non homologuée par la DNTT**.
> Les illustrations sont des photos routières réelles de Guinée (Wikimedia
> Commons, CC BY / CC BY-SA, voir
> `frontend/public/media/exam/guinea/realistic/ATTRIBUTION.md`).

---

## 1. Préparation

### La veille

```bash
cp .env.dev .env                 # si absent
scripts/demo.sh init             # génère .env.demo (clés aléatoires, non versionné)
scripts/demo.sh up               # stack locale : http://localhost:5173
scripts/demo.sh seed 15          # données de démo + première session live
scripts/demo.sh check            # répétition automatique : doit finir par 🎉
```

`check` rejoue tout le parcours (inscription → paiement → convocation →
contrôle d'entrée → examen → résultat), vérifie que les photos de l'examen
sont joignables, que les 8 régions remontent et que le journal d'audit est
intègre. **Ne pas faire la démonstration si `check` échoue.**

Faire ensuite une répétition complète à la main avec ce script, chronomètre
en main, puis enregistrer l'écran : c'est le plan B.

### Le matériel

- Portable branché au secteur, sortie vidéo testée, zoom navigateur à 110 %.
- **Connexion Internet requise** : les photos de l'examen sont servies en HTTPS
  par le frontend déployé (`DEMO_MEDIA_BASE_URL`). Prévoir un partage de
  connexion 4G en secours. La répétition de la veille met les photos en cache.
- Trois fenêtres de navigateur, déjà ouvertes et connectées :

| Fenêtre | Compte | Écran de départ |
|---|---|---|
| A — DNTT (normale) | `admin.national@coderoute.gov.gn` | `#/ministerial` |
| B — Chef de centre (autre profil) | `chef.conakry@coderoute.gov.gn` | `#/center` |
| C — Candidat (navigation privée) | aucun (inscription en direct) | `#/register` |

Mot de passe de tous les comptes de démonstration : `CodeRoute2026!`.

- Un terminal ouvert dans le dépôt, police agrandie, pour les deux commandes
  de l'étape 7.

### Cinq minutes avant de commencer

```bash
scripts/demo.sh live 12
```

Cette commande crée la **session du jour** au centre Kaloum 1, qui commence dans
12 minutes. Le code impose des fenêtres horaires réelles, qui expliquent ce délai :

| Action | Ouverte |
|---|---|
| Réservation par le candidat | jusqu'à l'heure de début (la session disparaît ensuite de la liste) |
| Contrôle d'entrée au centre | de début − 60 min à début + 30 min |
| Démarrage de l'examen | de début − 10 min à début + 45 min |

Avec `live 12` lancé à T0, il faut réserver avant T0 + 12 et démarrer
l'examen après T0 + 2. Le script ci-dessous réserve vers 4 min et démarre
l'examen vers 7 min. Si la démonstration commence en retard, relancer
`scripts/demo.sh live 12` juste avant de commencer.

---

## 2. Le script (15 minutes)

### 0:00 – 1:30 · Ouverture : la vue nationale

**Fenêtre A — `#/ministerial`, onglet « Vue nationale ».**

- Les 4 indicateurs du haut : alertes critiques, incidents de centre ouverts,
  événements d'examen à risque, alertes paiement.
- **Taux de réussite par région** : les 8 régions (Conakry, Boké, Kindia, Labé,
  Mamou, Faranah, Kankan, N'Zérékoré), calculés en direct à partir des examens
  de chaque centre, avec le volume d'examens et le nombre de centres.
- Les boutons **Rapport PDF** et **Rapport CSV** produisent le rapport
  institutionnel.

> Message : « La DNTT voit tout le territoire, en temps réel, depuis un seul écran. »

### 1:30 – 3:00 · Un citoyen s'inscrit

**Fenêtre C — `#/register`, onglet « Candidat ».**

1. Remplir le formulaire : prénom `Aïssatou`, nom `Barry`, une adresse e-mail,
   le téléphone `+224 621 …`, un numéro d'identité, catégorie **B**, ville
   `Conakry`, mot de passe (×2).
2. **Créer mon compte** → la référence officielle `GN-CODE-2026-……` s'affiche.
3. **Accéder à mon espace**, puis menu **Accueil** → carte
   **« Soumettre une pièce d'identité »** : type *Carte Nationale d'Identité*,
   saisir une référence de pièce → **Soumettre**.

> Message : « L'inscription prend une minute, depuis un téléphone. Sans identité
> vérifiée, le candidat ne pourra pas entrer en salle. »

### 3:00 – 3:30 · La DNTT vérifie l'identité

**Fenêtre A — `#/dossier`** (« Dossier d'État »), carte « Vérifications
d'identité » → bouton **Valider** sur la ligne de la pièce qui vient d'être
déposée (cliquer « Actualiser » si besoin).

### 3:30 – 5:30 · Réservation et paiement Mobile Money

**Fenêtre C — menu « Espace candidat » (`#/candidate`).**

1. « Choisissez votre centre d'examen » → **Centre d'Examen du Code de la
   Route — Kaloum 1 — Conakry**.
2. Le premier créneau est la session du jour → **Réserver**.
3. La carte « Rendez-vous confirmé » affiche la **référence de réservation** et
   le **code de vérification**. Frais : **150 000 GNF**, calculés par le serveur.
   Le navigateur ne peut pas fixer le prix.
4. Opérateur **Orange Money**, numéro `+224 622 000 111` → **Payer 150 000 GNF**
   → « Paiement confirmé — reçu GN-RECEIPT-… ».
5. **Télécharger ma convocation PDF (avec QR code)** → ouvrir le PDF : en-tête
   République de Guinée / DNTT, QR code, centre, code de vérification, consignes.

> Message : « Orange Money, MTN, Wave et PayDunya sont intégrés. Ici en mode
> simulé : aucun débit réel. Un double clic ne débite jamais deux fois. »

**Copier** la référence et le code de vérification (depuis la carte ou le PDF)
pour l'étape suivante.

### 5:30 – 6:30 · Contrôle d'entrée au centre

**Fenêtre B — `#/center`, carte « Valider l'entrée candidat ».**

- Le centre **Kaloum 1** est présélectionné : un agent ne voit que son centre.
- D'abord, montrer la fraude : coller la référence avec un **mauvais code** →
  **Valider l'entrée** → **ENTRÉE REFUSÉE**. Le motif s'affiche en code technique
  (`booking_not_found`) : c'est voulu, on ne dit pas au fraudeur ce qui est faux.
- Puis le bon code → **ENTRÉE AUTORISÉE**.
- Mentionner le bouton **« Scanner la convocation (QR) »** pour le jour réel.

> Message : « Pas de paiement, pas d'identité vérifiée, mauvais centre ou
> mauvais horaire : l'entrée est refusée, et chaque tentative est journalisée. »

### 6:30 – 9:30 · L'examen

**Fenêtre C — menu « Examen » (`#/exam`).**

1. Saisir la référence de réservation → **Démarrer l'examen officiel**.
2. Montrer : le bandeau « correction et score exclusivement côté serveur », le
   **chronomètre de 30 minutes synchronisé avec le serveur**, la photo réelle,
   le bouton **🔊 audio** et les **langues nationales** (Pular, Malinké,
   Soussou, Kissi, Kpelle, Toma).
3. Répondre aux 40 questions rapidement : touche **1** à **4** puis
   **Suivante**. Comptez environ 2 minutes.
4. **Soumettre l'examen** → résultat immédiat (score / 40, seuil 35) et
   correction détaillée de chaque question.

> Le résultat du candidat de démonstration sera vraisemblablement « NON ADMIS »,
> c'est attendu. L'étape suivante montre un candidat admis.

### 9:30 – 10:30 · Attestation et vérification publique

**Fenêtre C** : se déconnecter, puis se connecter avec
`mamadou.diallo@demo.coderoute.gn` (candidat pré-chargé, **admis 38/40**).

- Espace candidat → carte **« Vérifier un certificat »** : saisir
  `ATT-GN-CAND-2026-001` → **Vérifier** → « ADMIS — Mamadou Diallo · 38/40 ».
- Bouton **↓ PDF** de cette même carte → attestation de résultat « ADMIS(E) »
  (République de Guinée / DNTT, centre Kaloum 1, score 38/40).

> Message : « Un employeur ou un agent de police peut vérifier l'authenticité
> d'un résultat. »

### 10:30 – 12:30 · Supervision territoriale

**Fenêtre A — `#/admin`, onglet « Dashboard »**, carte « Supervision
nationale — activité par centre ».

1. Filtre **région → N'Zérékoré** : les centres de la région, leurs sessions,
   leurs examens, leur taux de réussite, et un **incident ouvert** (coupure
   d'électricité au centre N'Zérékoré 1, gravité haute). Il remonte aussi en
   tête de page comme alerte critique.
2. Filtre **Kankan** : incident de connexion internet ouvert.
3. Onglet **Paiements** : les paiements en attente ou à rapprocher, l'export
   CSV et le rapprochement financier.

> Message : « Un incident déclaré dans un centre de Forêt est visible à
> Conakry dans la minute. »

### 12:30 – 14:30 · Le journal d'audit infalsifiable

**Fenêtre A — `#/admin`, onglet « Audit ».**

1. Le journal retrace le paiement, le contrôle d'entrée et l'examen d'Aïssatou.
   Le champ de recherche filtre : `entry` (contrôles d'entrée), `payment`,
   `exam.submitted`.
2. **🔒 Vérifier l'intégrité** → bandeau vert « Journal intègre : N entrées
   chaînées ».
3. **Terminal**, en annonçant « je simule un agent malveillant qui modifie la
   base de données pour transformer un ajournement en admission » :

   ```bash
   scripts/demo.sh tamper
   ```

4. **🔒 Vérifier l'intégrité** → bandeau rouge « Altération détectée à
   l'entrée n°… (entry_hmac_mismatch) ».
5. Rétablir **immédiatement** :

   ```bash
   scripts/demo.sh restore
   ```

   puis **Vérifier l'intégrité** → de nouveau vert.

> Message : « Chaque événement est scellé et chaîné au précédent par une
> signature cryptographique. Une modification directe en base, même par un
> administrateur, est détectée et localisée. »

### 14:30 – 15:00 · Conclusion

Rappeler les trois messages :
1. un parcours candidat **entièrement numérique**, du téléphone jusqu'à la salle ;
2. une **supervision nationale par région**, en temps réel ;
3. une **traçabilité opposable** : contrôles d'entrée, correction côté serveur,
   journal infalsifiable.

Puis annoncer les prochaines étapes (section 4).

---

## 3. Dépannage pendant la démonstration

| Symptôme | Cause | Action |
|---|---|---|
| La session du jour n'apparaît pas dans les créneaux | Elle a déjà commencé | `scripts/demo.sh live 12`, puis re-sélectionner le centre |
| « Le démarrage de l'examen n'est pas ouvert pour cette session » | Plus de 10 min avant le début | Attendre l'heure affichée par `live`, ou `scripts/demo.sh live 5` puis refaire réservation et paiement |
| Entrée refusée : « identity_verification_required » | L'étape 3:00 a été sautée | `#/dossier` → **Valider** |
| Entrée refusée : « payment_required_before_checkin » | Paiement non effectué | Revenir à l'Espace candidat → **Payer** |
| Photos de l'examen absentes | Pas d'Internet | Partage 4G. Sinon, poursuivre : le texte des questions suffit |
| Bandeau rouge après la démonstration anti-fraude | `restore` oublié | `scripts/demo.sh restore` |
| Écran blanc ou erreur réseau | Stack arrêtée | `scripts/demo.sh up`, puis `scripts/demo.sh check` |

Si un blocage dure plus de 30 secondes, passer à la vidéo de la répétition
pour cette étape et reprendre la démonstration en direct à l'étape suivante.

## 4. Questions probables et réponses factuelles

- **« La banque de questions est-elle officielle ? »** Non. C'est une banque
  de démonstration : sa validation est une décision de la DNTT. La plateforme
  dispose du circuit d'homologation (statut par question, traçabilité de la
  banque par empreinte SHA-256 à chaque examen).
- **« Les paiements sont-ils réels ? »** Non, ils sont simulés. Les connecteurs
  Orange Money, MTN, Wave et PayDunya existent dans le code. Leur activation
  exige les contrats et les clés des opérateurs.
- **« Les données sont-elles réelles ? »** Non : candidats, centres et
  statistiques sont générés pour la démonstration.
- **« Le NINA est-il connecté ? »** Non. La vérification d'identité est
  aujourd'hui documentaire, et validée par un agent de la DNTT.
- **« Combien de candidats simultanés ? »** Voir `SCALING.md`. À ne pas chiffrer
  en séance sans test de charge sur l'infrastructure cible.

## 5. Remise à zéro

```bash
scripts/demo.sh restore                 # par précaution
scripts/demo.sh wipe                    # supprime la base de démo (confirmation « oui »)
scripts/demo.sh up && scripts/demo.sh seed 15 && scripts/demo.sh check
```

`scripts/demo.sh down` arrête la stack en conservant les données.

## 6. Comptes de démonstration

| Rôle | E-mail | Usage |
|---|---|---|
| Super administrateur | `super_admin@coderoute.gov.gn` | Paramétrage, homologation |
| Administrateur national (DNTT) | `admin.national@coderoute.gov.gn` | Vue nationale, identité, audit |
| Chef de centre Kaloum 1 | `chef.conakry@coderoute.gov.gn` | Contrôle d'entrée, incidents |
| Chef de centre Kindia 1 | `chef.kindia@coderoute.gov.gn` | Cloisonnement par centre |
| Opérateur Kaloum 1 | `operateur.conakry@coderoute.gov.gn` | Saisie au centre |
| Auto-école | `auto-ecole.kaloum@coderoute.gov.gn` | Élèves inscrits par l'auto-école |
| Candidat admis | `mamadou.diallo@demo.coderoute.gn` | Attestation 38/40 |
| Candidate payée | `mariam.soumah@demo.coderoute.gn` | Réservation payée, session à venir |

Mot de passe commun : `CodeRoute2026!`. Ces comptes n'existent que dans la
base locale de démonstration : le seed refuse de tourner hors
`ENVIRONMENT=development` (sauf dérogation explicite `ALLOW_DEMO_SEED_NON_DEV`).
Ils ne doivent jamais être créés sur un environnement accessible depuis Internet.
