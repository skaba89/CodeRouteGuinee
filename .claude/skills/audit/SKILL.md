---
name: audit
description: Audit en lecture seule d'un module, d'un flux ou du dépôt CodeRoute (fonctionnalités, examen, banque, interfaces, sécurité, CI, résilience, secrets, réglementation). Produit un état classé et des risques par criticité avec preuves fichier:ligne.
---

# Audit

Aucune modification de fichier applicatif pendant un audit.

## Grille (10 points)
1. Fonctionnalités réellement implémentées (routeurs `backend/app/routers/`, pages `frontend/src/pages/`).
2. Écarts README ↔ code (chiffres, commandes, comptes).
3. Moteur d'examen : `exam_engine.py`, `routers/exams.py`, `routers/exam_runtime.py`, gardes montés dans `routers/__init__.py`.
4. Banque, médias, traductions : `models_question.py`, `question_bank_gn.py`, `media_*`, `question_i18n.py`.
5. Interfaces candidat, centre, auto-école, administration.
6. Authentification, rôles, périmètre centre, antifraude.
7. Migrations (`alembic/versions`, une seule tête), tests, CI (`.github/workflows`), déploiement (`render.yaml`, `entrypoint.sh`).
8. Perte de réponses et défaillance réseau (autosauvegarde, reprise, expiration, edge).
9. Données de démo, identifiants et secrets exposés : lister `git ls-files | grep .env` **sans lire** les fichiers réels.
10. Exigences réglementaires guinéennes à confirmer (ne rien supposer).

## Classement
✅ implémentée et testée (test cité) · 🟡 partielle · ❌ absente · ❔ non vérifiée.
Risques : critique (bloque un examen officiel) / élevé / moyen / faible.

## Sortie
Tableaux avec preuve `fichier:ligne` pour chaque ligne, puis une section « Limites de l'audit » (ce qui n'a pas été exécuté).
Référence : `docs/audit/AUDIT_EXISTANT.md`.
