# Frontend TypeCheck — Phase 1 Audio/Langues

**Date :** 2026-06-21  
**Branche :** fix-frontend-audio-typecheck  
**Objectif :** corriger les erreurs TypeScript introduites lors de l'intégration audio (Phase 1)

---

## Commandes exécutées

```bash
git checkout main
git pull origin main
cd frontend
npm ci
npm run typecheck
npm run build
```

---

## Erreurs initiales (3)

```
src/App.tsx(117,12): error TS2304: Cannot find name 'AudioToggle'.
src/App.tsx(123,10): error TS2552: Cannot find name 'LocaleAudioSwitcher'. Did you mean 'LocaleSwitcher'?
src/components/AudioButton.tsx(8,8): error TS2459: Module '"../audio"' declares 'Locale' locally, but it is not exported.
```

## Corrections appliquées

### 1. `src/App.tsx` — imports manquants
`AudioToggle` et `LocaleAudioSwitcher` étaient utilisés (lignes 117 et 123) mais jamais importés.

```diff
  import { LocaleSwitcher } from './components/LocaleSwitcher';
+ import { AudioToggle, LocaleAudioSwitcher } from './components/AudioButton';
```

### 2. `src/components/AudioButton.tsx` — source de l'import `Locale` incorrecte
`Locale` était importé depuis `../audio` mais ce module ne l'exporte pas — il l'utilise depuis `../i18n`.
Correction : déplacer l'import vers `../i18n/index.ts` qui est la source canonique.

```diff
  import {
    getAudioEnabled, isAudioLocale, isTTSAvailable,
    preloadVoices, setAudioEnabled, speak, speakQuestion, stop,
-   type Locale,
  } from '../audio';
- import { useLocale, SUPPORTED_LOCALES } from '../i18n';
+ import { useLocale, SUPPORTED_LOCALES, type Locale } from '../i18n';
```

---

## Résultat typecheck

```
$ npm run typecheck
> tsc --noEmit
(aucune erreur — exit 0)
```

## Résultat build

```
$ npm run build
✓ 31 modules transformed.
dist/index.html                   2.44 kB │ gzip: 1.09 kB
dist/assets/index-*.css          13.13 kB │ gzip: 3.17 kB
dist/assets/pages-*.js          122.22 kB │ gzip: 28.26 kB
dist/assets/vendor-react-*.js   181.89 kB │ gzip: 57.20 kB
✓ built in 734ms
```

---

## Conclusion : Phase 1 OK

- 0 erreur TypeScript
- Build production réussi
- Aucune logique métier modifiée
- Aucune refonte UI
- La source canonique de `Locale` est désormais `src/i18n/index.ts` dans tous les modules
