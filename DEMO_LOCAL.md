# Demo locale CodeRoute Guinee

Ce guide sert a valider une premiere version presentable en local avant une demonstration.

## 1. Demarrer le projet

```bash
docker compose up --build
```

Endpoints utiles :

- API : http://localhost:8000
- Swagger : http://localhost:8000/docs
- Frontend : http://localhost:5173

## 2. Charger les donnees de demonstration

Dans un second terminal :

```bash
docker compose exec backend python -m app.seed_demo
```

Le script cree ou reutilise :

- un administrateur national ;
- un centre agree a Conakry ;
- un candidat de demonstration ;
- une session d'examen ;
- une reservation avec code de verification ;
- un paiement Mobile Money sandbox ;
- une tentative d'examen deja soumise ;
- une petite banque de questions.

## 3. Tester rapidement l'API en local

```bash
python scripts/smoke_local.py
```

Le test verifie :

- health API ;
- dashboard ;
- convocation ;
- paiement sandbox ;
- validation entree centre ;
- resume examen.

## 4. Scenario de demonstration recommande

### Accueil

Presenter CodeRoute Guinee comme une plateforme nationale d'examen du code de la route : centres agrees, supervision administrative, tracabilite et anti-fraude.

### Connexion

Aller sur :

```text
http://localhost:5173/#/login
```

Utiliser le compte admin affiche par le script de seed.

### Admin

Aller sur :

```text
http://localhost:5173/#/admin
```

Montrer :

- les candidats ;
- les centres agrees ;
- les sessions ;
- les indicateurs d'examen ;
- les entrees centre.

### Candidat

Aller sur :

```text
http://localhost:5173/#/candidate
```

Montrer :

- paiement Mobile Money sandbox ;
- recu ;
- telechargement convocation PDF.

### Centre agree

Aller sur :

```text
http://localhost:5173/#/center
```

Utiliser :

```text
Reference : CRG-BOOK-DEMO-001
Code verification : CRG-VERIFY-DEMO-001
Centre : CRG-CONAKRY-001
```

Montrer la validation d'entree et la tracabilite.

### Resultats

Aller sur :

```text
http://localhost:5173/#/results
```

Montrer le resume d'examen, le score et la logique de reussite/echec.

## 5. Points a annoncer comme prochaines evolutions

- remplacement complet du mode demonstration par l'authentification reelle ;
- protection stricte des routes backend par role ;
- certificat PDF apres reussite ;
- supervision anti-fraude avancee ;
- migrations Alembic et deploiement production.
