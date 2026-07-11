# Plan de reprise après sinistre (PRA) — CodeRoute Guinée

Ce document définit la conduite à tenir en cas d'incident grave affectant
la plateforme : panne d'hébergement, corruption ou perte de données,
cyberattaque, indisponibilité prolongée. L'objectif est qu'une équipe, même
sous pression, sache exactement quoi faire, dans quel ordre, et à qui
s'adresser — au lieu d'improviser le pire jour possible.

> Principe directeur : on ne teste pas un PRA le jour du sinistre. Les
> procédures ci-dessous doivent être répétées à froid (voir §7).

---

## 1. Objectifs de reprise (RTO / RPO)

Deux chiffres cadrent tout plan de reprise :

- **RTO (Recovery Time Objective)** — délai maximal acceptable pour
  rétablir le service après un sinistre.
- **RPO (Recovery Point Objective)** — quantité maximale de données
  qu'on accepte de perdre (mesurée en temps).

Cibles recommandées par phase de déploiement :

| Phase | RTO cible | RPO cible |
|---|---|---|
| Pilote (1-3 centres) | 4 heures | 24 heures (backup quotidien) |
| Régional (10-20 centres) | 2 heures | 6 heures |
| National (135 centres) | 30 minutes | 15 minutes (réplication + PITR) |

Au national, atteindre RPO 15 min impose une **réplication continue** de la
base (au-delà du backup quotidien) et un point-in-time recovery (PITR),
proposés nativement par l'hébergeur PostgreSQL (Neon).

---

## 2. Rôles et contacts (à compléter avant mise en production)

| Rôle | Responsabilité | Contact |
|---|---|---|
| Astreinte technique | Diagnostic et exécution de la reprise | _______ |
| Responsable données (DNTT) | Décision sur les données officielles | _______ |
| Hébergeur (Render / Neon) | Support infrastructure | _______ |
| Opérateurs Mobile Money | Incidents de paiement | _______ |
| Communication DNTT | Information des centres et candidats | _______ |

Une seule personne **décide** de déclencher une restauration (le
responsable données), sur proposition de l'astreinte technique. Ceci évite
les restaurations paniquées et non concertées.

---

## 3. Détection : comment on sait qu'il y a un incident

- **Sentry** capture les erreurs applicatives en temps réel (alertes).
- **`/health`** — sonde de vie (le service répond-il ?).
- **`/health/readiness`** — sonde de disponibilité (base, schéma,
  migrations, configuration OK ?). À interroger par une supervision externe.
- **`/admin/ops/audit-chain/verify`** — intégrité du journal d'audit
  (détecte une altération de données sensibles).
- **Signalements terrain** — un centre qui ne peut plus valider d'entrées.

Mettre en place une **supervision externe** (uptime monitoring) qui appelle
`/health` toutes les minutes et alerte l'astreinte en cas d'échec.

---

## 4. Scénarios et procédures

### Scénario A — Le service est indisponible (mais les données sont saines)
*Cause typique : plantage applicatif, mauvais déploiement, saturation.*

1. Vérifier `/health` et `/health/readiness`.
2. Consulter Sentry pour la cause (exception, saturation).
3. Si dû à un déploiement récent : **revenir à la version précédente**
   (rollback) via l'hébergeur.
4. Si saturation : augmenter temporairement les ressources (workers,
   instance) — voir `load_testing.md`.
5. Vérifier le retour à la normale via `/health/readiness`.
6. Post-mortem (§6).

### Scénario B — Corruption ou perte de données
*Cause typique : bug de migration, suppression accidentelle, défaillance base.*

1. **Isoler** : mettre le service en maintenance pour stopper l'écriture.
2. **Diagnostiquer l'étendue** : quelles tables, depuis quand. Utiliser
   `/admin/ops/audit-chain/verify` pour détecter une altération d'audit.
3. **Décision** (responsable données) : restaurer ou non.
4. **Restaurer** depuis le dernier backup sain (procédure détaillée dans
   `backup_restore.md`) :
   ```
   python scripts/postgres_backup.py restore <backup> --confirm-restore --clean
   ```
5. **Vérifier** : `/health/readiness` OK, chaîne d'audit valide, contrôle
   par sondage de données clés (derniers résultats, paiements).
6. **Mesurer la perte** (RPO réel) et informer la DNTT.
7. Remettre le service en ligne. Post-mortem.

### Scénario C — Cyberattaque / compromission suspectée
1. **Isoler immédiatement** : couper l'accès public si nécessaire.
2. **Ne pas détruire les preuves** : conserver les logs, la chaîne d'audit.
3. Vérifier l'intégrité via `/admin/ops/audit-chain/verify` — une chaîne
   rompue prouve une altération de données sensibles.
4. **Rotation immédiate de tous les secrets** (voir `SECURITY_ROTATION.md`).
5. Restaurer depuis un backup antérieur à la compromission si nécessaire.
6. Notification aux autorités compétentes et à la DNTT.
7. Audit de sécurité avant remise en service.

### Scénario D — Indisponibilité de l'hébergeur
*Render ou Neon totalement inaccessible.*

1. Vérifier le statut de l'hébergeur (page de statut officielle).
2. Si panne prolongée : au national, basculer sur l'**instance de secours**
   (site de reprise) — d'où l'importance de la réplication multi-région.
3. Informer les centres via le canal de communication DNTT (les sessions du
   jour peuvent devoir être reportées).
4. Documenter pour renégocier le SLA de l'hébergeur si récurrent.

---

## 5. Sauvegardes : ce sur quoi la reprise s'appuie

- **Fréquence** : quotidienne automatique (workflow CI), plus manuelle à la
  demande.
- **Vérification** : chaque backup est contrôlé automatiquement, et un test
  de restauration complet (round-trip) est exécuté quotidiennement — la
  capacité de reprise est donc **prouvée en continu**, pas supposée.
- **Rétention** : 7 jours en CI ; recommandation nationale : stockage
  externe chiffré (S3/GCS) avec 12 mois de rétention pour les obligations
  légales de conservation des résultats.
- **Point-in-time recovery** : à activer au national via Neon, pour un RPO
  de quelques minutes.

Détails opérationnels : `backup_restore.md`.

---

## 6. Après l'incident : post-mortem sans blâme

Chaque incident majeur donne lieu à un post-mortem écrit, orienté
amélioration (pas recherche de coupable) :

- Chronologie des faits (détection → résolution).
- Cause racine.
- Impact réel (durée d'indisponibilité, données perdues, centres affectés).
- Ce qui a bien fonctionné, ce qui a manqué.
- Actions correctives datées et assignées.

---

## 7. Répétition à froid (le plus important)

Un PRA jamais testé échoue le jour J. Calendrier recommandé :

- **Trimestriel** : exécuter une restauration complète sur un
  environnement de secours, chronométrée. Comparer le temps obtenu au RTO
  cible et ajuster.
- **Après chaque changement majeur** d'infrastructure : re-tester la
  restauration.
- **Vérifier régulièrement** l'intégrité de la chaîne d'audit.

Consigner chaque exercice (date, durée, RTO mesuré, anomalies) pour prouver
à la DNTT la maturité opérationnelle du dispositif.

---

## 8. Checklist de préparation (avant le national)

- [ ] Contacts d'astreinte renseignés (§2)
- [ ] Supervision externe branchée sur `/health` (alerte < 1 min)
- [ ] Stockage externe chiffré des backups configuré
- [ ] Rétention 12 mois en place
- [ ] Point-in-time recovery (Neon) activé
- [ ] Instance de secours / réplication multi-région (national)
- [ ] Premier exercice de restauration à froid réalisé et chronométré
- [ ] RTO/RPO réels mesurés et validés avec la DNTT
- [ ] Procédure de rotation des secrets testée
