# Tests UI Playwright

Cette suite ajoute des smoke tests navigateur pour verifier que l'interface CodeRoute Guinee reste utilisable en mode demo.

## Commande

```bash
cd frontend
npm run test:e2e
```

## Couverture

- chargement de la page d'accueil nationale ;
- navigation vers les espaces candidat, centre et admin ;
- verification des actions visibles principales ;
- changement de role demo ;
- refus d'acces a l'administration pour un candidat ;
- verification des ecrans examen et resultats.
