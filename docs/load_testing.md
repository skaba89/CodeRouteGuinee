# Analyse de charge et dimensionnement national

Ce document présente les mesures de charge réalisées sur CodeRoute Guinée
et les recommandations de dimensionnement pour un déploiement à l'échelle
des 135 centres du territoire.

---

## 1. Ce qui a été mesuré et optimisé

### Détection et correction de N+1 (goulets d'étranglement cachés)

Deux endpoints critiques exécutaient trop de requêtes SQL — le type de
défaut invisible en test unitaire mais qui sature la base sous charge
réelle :

| Endpoint | Avant | Après | Gain |
|---|---|---|---|
| `availability/{center}` (30 sessions) | **33 requêtes** | **4 requêtes** | **8×** |
| `bookings/my` (20 réservations) | jusqu'à 41 requêtes | 3 requêtes | ~13× |

`availability` est le chemin le plus sollicité le jour d'une session :
chaque candidat le charge pour voir les places disponibles. Diviser sa
charge base par 8 est déterminant à l'échelle nationale.

Correction : remplacement des boucles « une requête par élément » par une
seule requête agrégée (`GROUP BY`) ou un chargement en masse (`IN`).

### Mesure de concurrence (PostgreSQL 16 réel)

Endpoint `availability`, concurrence croissante :

| Concurrence | p50 | p95 | Erreurs |
|---|---|---|---|
| 1 | 7 ms | 14 ms | 0 |
| 10 | 61 ms | 110 ms | 0 |
| 50 | 319 ms | 494 ms | 0 |
| 100 | 746 ms | 899 ms | 0 |

**Lecture honnête de ces chiffres :**

- **0 erreur à tous les niveaux** : le système est stable, rien ne casse
  ni ne perd de requête, même à 100 connexions simultanées.
- Le débit plafonne (~140 req/s) car le test tourne dans **un seul
  processus** Python (limite du GIL). La latence croît car les requêtes
  font la queue derrière un unique worker.
- **Ce test valide l'efficacité du CODE** (peu de requêtes, aucune
  erreur), pas la capacité absolue de l'infrastructure.

---

## 2. Capacité réelle en production

En production, l'application ne tourne pas en process unique : **gunicorn
lance plusieurs workers**. La capacité se multiplie donc par le nombre de
workers.

Formule (voir `backend/gunicorn.conf.py`) :

```
workers = (2 × nombre_de_CPU) + 1
```

| Plan | CPU | Workers | Débit indicatif |
|---|---|---|---|
| Render starter | ~1 | 3 | ~400 req/s |
| Render standard | 2 | 5 | ~700 req/s |
| Render pro | 4 | 9 | ~1 200 req/s |

Contrainte à respecter impérativement :

```
workers × (DB_POOL_SIZE + DB_MAX_OVERFLOW) ≤ max_connections PostgreSQL − 10
```

Avec les valeurs par défaut (pool 20, overflow 30 = 50 par worker) et
9 workers = 450 connexions : il faut une base PostgreSQL acceptant
≥ 460 connexions, ou réduire le pool. **C'est le point de rupture n°1 à
surveiller** : dépasser `max_connections` provoque des erreurs immédiates.

---

## 3. Recommandations de dimensionnement par vague

### Vague 1 — Pilote (1 à 3 centres, ~100 candidats/jour)
- Plan **starter** suffit (3 workers, ~400 req/s).
- Pool DB par défaut (20+30).
- Objectif : valider le service, pas la charge.

### Vague 2 — Régional (10-20 centres, ~1 000 candidats/jour)
- Plan **standard** (2 CPU, 5 workers).
- Vérifier `max_connections` de la base ≥ 260.
- Activer le cache sur les données peu changeantes (liste des centres).

### Vague 3 — National (135 centres, pics de plusieurs milliers simultanés)
- Plan **pro** ou supérieur, voire **plusieurs instances** derrière un
  répartiteur de charge (Render scale horizontal).
- Base PostgreSQL dimensionnée : `max_connections` élevé + **PgBouncer**
  (pool de connexions côté base) pour absorber les pics sans épuiser les
  connexions.
- Envisager un **CDN** pour les assets frontend et un **cache Redis** pour
  les endpoints de lecture chauds (availability, liste des centres).
- Répartir les sessions dans la journée (créneaux échelonnés) pour lisser
  les pics plutôt que tout concentrer à 9h.

---

## 4. Comment relancer le test de charge

```bash
# Contre une base PostgreSQL de test représentative
cd backend
DATABASE_URL="postgresql+psycopg://user:pass@host:5432/db" \
  python ../scripts/load_test.py
```

Pour mesurer la **vraie capacité de production**, lancer un outil externe
(k6, Locust en mode distribué, ou `ab`) contre l'URL Render réelle avec
plusieurs workers actifs — c'est le seul moyen de mesurer l'infra complète
(workers + base + réseau), là où le test intégré ne mesure qu'un process.

---

## 5. Points de surveillance en production

- **Connexions PostgreSQL** : alerte si proche de `max_connections`.
- **Latence p95** : alerte si > 1 s sur les endpoints candidats.
- **Taux d'erreur 5xx** : doit rester à 0 ; toute hausse = saturation.
- **Sentry** est déjà branché pour capturer les erreurs en temps réel.
