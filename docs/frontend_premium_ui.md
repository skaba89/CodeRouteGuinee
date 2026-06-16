# Frontend Premium UI/UX

Cette évolution ajoute une couche visuelle premium au frontend sans modifier la logique métier existante.

## Objectifs

- Améliorer le rendu institutionnel de CodeRoute Guinée.
- Renforcer le responsive mobile.
- Moderniser la navigation, les cartes KPI, les formulaires et les tableaux.
- Conserver les pages et routes React existantes.

## Fichiers modifiés

- `frontend/src/premium-ui.css` : nouvelle couche d'overrides visuels.
- `frontend/src/main.tsx` : import de la couche premium après `styles.css`.

## Principes UI

- Palette institutionnelle : bleu profond, vert, blanc et doré.
- Cartes plus lisibles avec ombres douces.
- Navigation responsive avec meilleure lisibilité mobile.
- Formulaires plus accessibles et plus grands sur mobile.
- Amélioration des états visuels : badges, panels, tableaux et cartes.

## Test recommandé

```bash
cd frontend
npm install
npm run build
npm run test:e2e
```
