---
name: migration-check
description: Contrôle d'une migration Alembic ou d'une modification de modèle SQLAlchemy CodeRoute — une seule tête, additive, réversible, idempotente, compatible pendant le déploiement, sans perte de données.
---

# Contrôle de migration

1. **Une seule tête** : `cd backend && alembic heads` (sur une base jetable uniquement).
2. **Nouvelle révision** : jamais modifier un fichier existant de `backend/alembic/versions/`. Identifiant de révision séquentiel (`revision = "0018"`), `down_revision` = tête actuelle ; fichier `0018_description.py` comme `0016`/`0017` (les révisions plus anciennes sont préfixées par une date).
3. **Additive d'abord** : nouvelles colonnes nullable ou avec défaut serveur ; suppression ou renommage seulement dans une révision ultérieure, après une version de compatibilité.
4. **Réversible** : `downgrade()` complet ; tester `upgrade head → downgrade -1 → upgrade head` sur PostgreSQL 16 jetable.
5. **Données** : migration de données idempotente et par lots ; aucune perte sur les tentatives, traces, résultats ou journaux d'audit (les journaux sont append-only : pas d'UPDATE/DELETE).
6. **Modèle ↔ migration** : le modèle SQLAlchemy et la migration décrivent le même schéma (index, contraintes, types).
7. **Déploiement** : migrations exécutées par `scripts/predeploy.sh` (pré-déploiement Render), jamais au démarrage de l'API ; ancien code compatible avec le nouveau schéma.
8. **Tests** : un test qui crée des données avec l'ancien format et vérifie leur lecture après migration.

Sortie : liste cochée des 8 points, avec les blocages.
