# Guide simple des tests end-to-end

Ce guide permet de lancer la recette complète sans devoir retenir toutes les commandes backend et frontend.

## Commande recommandee

Depuis la racine du projet `CodeRouteGuinee`:

```powershell
.\scripts\run_full_recette.cmd
```

Cette commande execute:

1. les migrations de base de donnees;
2. tous les tests backend;
3. le typecheck frontend;
4. le build frontend;
5. les tests navigateur Playwright.

## Commande rapide avant une demo

```powershell
.\scripts\run_full_recette.cmd -Scope smoke
```

Le fichier `.cmd` lance le script PowerShell avec l autorisation locale necessaire, ce qui evite le blocage Windows sur les scripts non signes.

Le mode `smoke` verifie les parcours prioritaires:

- inscription candidat dans un centre;
- examen multimedia avec 40 questions;
- recette institutionnelle pilote;
- parcours candidat complet;
- monitoring exploitation;
- migrations;
- E2E navigateur frontend.

## Preview

Apres une recette reussie:

```text
http://127.0.0.1:4173/#/exam
```

## Si Playwright echoue

Sur Windows, Chromium peut etre bloque par les permissions. Dans Codex, il faut autoriser l execution du navigateur quand la demande apparait.

## Ce qu il faut considerer comme OK

- La commande se termine par `Recette terminee avec succes`.
- Aucun test ne finit en `failed`.
- La preview affiche la page examen avec une image ou une video dans la question.
