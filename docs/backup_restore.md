# Guide — Sauvegarde et restauration de la base de données

Ce document décrit la stratégie de sauvegarde de CodeRoute Guinée et la
**procédure de restauration vérifiée**. Principe fondamental : un backup
qui n'a jamais été restauré n'est pas un backup. C'est pourquoi la
restauration est testée automatiquement à chaque exécution.

---

## 1. Ce qui est sauvegardé

Toute la base PostgreSQL : candidats, réservations, paiements, examens,
résultats, questions, centres, audit. Format `pg_dump --format=custom`
(compressé, restaurable sélectivement via `pg_restore`).

## 2. Quand

- **Automatique** : chaque jour à 02h00 UTC (03h00 Conakry) via GitHub
  Actions (`.github/workflows/backup.yml`).
- **Manuel** : déclenchable à tout moment (workflow_dispatch, ou script).

Chaque exécution : (1) crée le backup, (2) vérifie son intégrité,
(3) **teste une restauration réelle** (round-trip), (4) archive le fichier
7 jours, (5) alerte en cas d'échec.

## 3. Création manuelle d'un backup

```bash
cd backend
DATABASE_URL="postgresql://user:pass@host:5432/coderoute" \
  python scripts/postgres_backup.py \
    --backup-dir /var/backups/coderoute \
    --retention-days 7 \
    backup
```

Le script crée le fichier, le vérifie automatiquement, puis applique la
rétention (supprime les backups de plus de 7 jours, en gardant toujours au
moins le plus récent).

## 4. Vérification d'intégrité

```bash
python scripts/postgres_backup.py --backup-dir /var/backups/coderoute --verify
```

Contrôle que le dernier backup est une archive `pg_dump` valide et lisible
(via `pg_restore --list`). Un fichier vide ou corrompu échoue.

## 5. Restauration (procédure d'incident)

> ⚠️ La restauration **écrase** les données existantes. À n'exécuter que
> lors d'une reprise après incident, sur la bonne base.

```bash
DATABASE_URL="postgresql://user:pass@host:5432/coderoute" \
  python scripts/postgres_backup.py \
    restore /var/backups/coderoute/coderoute-guinee-XXXX.backup \
    --confirm-restore --clean
```

- `--confirm-restore` : obligatoire (garde-fou contre une exécution accidentelle).
- `--clean` : supprime proprement les objets existants avant restauration
  (`--clean --if-exists` en interne), ce qui rend l'opération fiable que la
  base soit vide, partielle ou complète.

## 6. Pourquoi le round-trip est testé

Le point le plus important : la CI ne se contente pas de créer un fichier.
À chaque exécution, elle :

1. insère une donnée témoin,
2. crée un backup,
3. **détruit** la donnée,
4. restaure depuis le backup,
5. vérifie que la donnée témoin est **revenue à l'identique**.

Si la restauration échoue, la CI échoue et alerte. Cela garantit que le
jour d'un vrai incident, la restauration fonctionnera — ce n'est pas une
supposition, c'est prouvé quotidiennement.

## 7. Recommandations production

- **Stockage externe** : les artefacts CI sont conservés 7 jours. Pour une
  base nationale, répliquer les backups vers un stockage durable et
  géographiquement distinct (S3, GCS, ou équivalent) avec chiffrement au repos.
- **Rétention longue** : garder au moins un backup mensuel sur 12 mois pour
  les obligations légales de conservation des résultats d'examen.
- **Test de restauration trimestriel** : au-delà de la CI, réaliser une
  restauration complète sur un environnement de secours une fois par
  trimestre, chronométrée, pour connaître le temps de reprise réel (RTO).
- **Neon (base actuelle)** : Neon propose aussi des sauvegardes et un
  point-in-time recovery natifs — les combiner avec ce script pour une
  double protection.
