# Guide — Enregistrement audio des questions en langues nationales

Ce document explique comment produire et intégrer les enregistrements audio
des questions d'examen dans les langues nationales guinéennes (Pular,
Malinké, Soussou, Kissi, Kpelle, Toma).

---

## 1. Pourquoi c'est déterminant

Une part importante de la population guinéenne **parle** une langue
nationale sans la **lire**. Un examen écrit, même traduit, exclut encore ces
citoyens. L'audio lève cette barrière : le candidat *entend* la question
dans sa langue et peut passer l'examen.

C'est le différenciateur le plus fort de la plateforme. Aucune solution
internationale ne le propose pour la Guinée.

---

## 2. Choix de conception : l'écrit reste en français, l'oral suit la langue

Le texte des questions est **toujours affiché en français**. Seul l'**audio**
est en langue nationale.

Ce choix est délibéré : les langues nationales guinéennes n'ont pas de
standard d'écriture largement partagé. Un texte écrit en Pular ou en
Malinké dérouterait beaucoup de lecteurs et introduirait un risque
d'ambiguïté juridique sur le sens exact des questions d'examen. À l'inverse,
l'oral est **immédiatement compris** par tous ceux qui parlent la langue.

Un candidat pular **voit** donc la question en français et **l'entend** en
pular.

## 3. Comment le système fonctionne

Trois niveaux, avec repli automatique — **aucune question n'est jamais
muette** :

1. **Enregistrement par un locuteur natif** (le meilleur) — le candidat
   entend sa vraie langue. C'est ce que ce guide permet de produire.
2. **Synthèse vocale du navigateur** (repli automatique) — disponible
   immédiatement, mais prononce le texte avec une voix française.
3. **Texte affiché** — toujours présent.

Le passage de l'un à l'autre est automatique : dès qu'un enregistrement
existe pour une question dans la langue du candidat, il est joué. Sinon, la
synthèse vocale prend le relais.

---

## 4. Ce qu'il faut enregistrer

Pour chaque question et chaque langue, un fichier audio contenant :

1. L'énoncé de la question ;
2. Les options de réponse, annoncées par leur lettre (« A… », « B… »).

Prononciation posée, débit modéré (un candidat doit pouvoir suivre).

**Volume** : 200 questions × nombre de langues. Commencer par les **40
questions officielles** de l'examen et les **langues les plus parlées**
(Pular, Malinké, Soussou) donne déjà une couverture majeure.

---

## 5. Recommandations de production

- **Locuteurs natifs** de chaque langue, à la diction claire.
- **Validation par la DNTT** : la traduction orale doit être fidèle au sens
  juridique de la question (une nuance perdue peut fausser l'examen).
- **Format** : MP3, mono, 64–128 kbps suffisent (fichiers légers = important
  pour la connectivité guinéenne).
- **Nommage clair** par question et par langue.
- **Durée** : viser moins d'une minute par question.

---

## 6. Où héberger les fichiers

Deux options, toutes deux prises en charge :

**Option A — Hébergement externe (recommandé)**
Déposer les fichiers sur un hébergement de médias (Cloudinary, ou tout CDN),
puis renseigner l'URL complète (https://…) dans la question. Avantage :
diffusion rapide, pas de charge sur le serveur applicatif.

**Option B — Fichiers servis par l'application**
Placer les fichiers selon la convention `/audio/{langue}/{id_question}.mp3`
(ex. `/audio/ff/q01.mp3`). Le système les trouve automatiquement, sans
configuration.

---

## 7. Comment intégrer un enregistrement

Via l'API d'administration, sur une question donnée :

```
PUT /api/v1/questions/{id}/audio
{
  "ff":  "https://…/q01_pular.mp3",
  "man": "/audio/man/q01.mp3"
}
```

Une valeur vide (`""`) supprime l'enregistrement d'une langue.

Sécurité : seules les URL `https://` ou les chemins `/audio/…` sont
acceptés (protection contre les injections).

---

## 8. Vérification

Après intégration :

1. Se connecter avec la langue concernée (ex. Pular).
2. Lancer un entraînement ou un examen.
3. La question doit être **lue par l'enregistrement natif**.
4. Sur une question sans enregistrement, la synthèse vocale doit prendre le
   relais (aucun silence).

---

## 9. Feuille de route suggérée

| Étape | Portée | Effort |
|---|---|---|
| 1 | 40 questions officielles × Pular | ~40 enregistrements |
| 2 | + Malinké, Soussou | ~80 enregistrements |
| 3 | Les 200 questions × 3 langues principales | ~600 enregistrements |
| 4 | Langues forestières (Kissi, Kpelle, Toma) | selon besoins régionaux |

Chaque étape apporte une valeur immédiate : le système fonctionne avec des
enregistrements partiels, en complétant par la synthèse vocale.
