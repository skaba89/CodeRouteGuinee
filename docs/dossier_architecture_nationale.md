# CodeRoute Guinée — Dossier d'architecture nationale

**Plateforme numérique nationale de l'examen du code de la route**
Document de présentation à la Direction Nationale des Transports Terrestres (DNTT)

*Édité par DataSphere Innovation — version de référence, juillet 2026*

---

## 1. Résumé exécutif

CodeRoute Guinée est une plateforme complète et opérationnelle pour
dématérialiser l'examen national du code de la route, de l'inscription du
candidat jusqu'à la délivrance de l'attestation. Le système est conçu pour
les réalités guinéennes : paiement par Mobile Money, langues nationales,
connectivité intermittente, et déploiement progressif sur les 135 centres
du territoire.

Contrairement aux solutions internationales génériques, la plateforme est
pensée pour la Guinée : elle parle les langues du pays, s'adapte au réseau,
et intègre les moyens de paiement locaux. C'est un atout de souveraineté
numérique — une infrastructure publique maîtrisée localement.

**En chiffres :** ~32 000 lignes de code, 843 tests automatisés (0 échec,
83 % de couverture), 8 langues, 164 points d'API, chaîne de traçabilité
inviolable. Le socle technique est prêt pour un pilote encadré.

---

## 2. Ce que la plateforme fait aujourd'hui

**Parcours candidat complet et prouvé de bout en bout :**
inscription (candidat libre ou via auto-école), consultation des centres et
créneaux, réservation, paiement Mobile Money, convocation officielle (PDF
avec QR code), passage de l'examen (40 questions illustrées, répartition
officielle par catégorie), résultat immédiat, attestation.

**Pour les centres :** validation d'entrée des candidats par scan du QR de
la convocation ou saisie manuelle, avec contrôle anti-fraude.

**Pour la DNTT :** tableau de bord de supervision nationale (activité par
centre, taux de réussite, incidents), rapports institutionnels, validation
officielle des questions, supervision financière et anti-fraude.

---

## 3. Les quatre garanties d'un système d'État

Un examen national n'est pas un logiciel ordinaire : le permis d'un citoyen
en dépend, il manipule de l'argent public et des données personnelles. Nous
avons traité en priorité les quatre exigences qui distinguent un produit
commercialisable à l'échelle d'un État.

### 3.1 Contenu certifié et traçable
Chaque question suit un circuit de validation officiel (brouillon → soumis →
approuvé par l'autorité DNTT), avec traçabilité de qui valide et quand.
**Seules les questions officiellement approuvées sont tirées à l'examen
réel.** Le contenu de l'examen est donc juridiquement défendable.

### 3.2 Paiement infaillible
Intégration des opérateurs guinéens (Orange Money, MTN MoMo, Wave). Une
protection stricte garantit qu'**un citoyen ne peut jamais être débité deux
fois** pour une même réservation, même en cas de double-clic ou de relance
réseau — prouvé par test automatique.

### 3.3 Données récupérables (sauvegarde vérifiée)
Sauvegarde quotidienne automatique de toute la base. Point essentiel : la
restauration est **testée chaque jour** par un cycle complet (une donnée
témoin est détruite puis restaurée et vérifiée). Un backup jamais restauré
n'est pas un backup ; ici, la capacité de reprise est prouvée, pas supposée.

### 3.4 Tenue à l'échelle
Les chemins les plus sollicités ont été optimisés (division par 8 du nombre
de requêtes sur l'écran de réservation). La stabilité a été mesurée sous
charge (0 erreur jusqu'à 100 connexions simultanées). Le dimensionnement
pour le national est documenté (voir §7).

---

## 4. Ce qui nous place devant la concurrence mondiale

### 4.1 L'examen dans la langue du candidat
La plateforme sert les questions dans les **langues nationales
guinéennes** — Pular, Malinké, Soussou, et d'autres — avec repli
automatique sur le français. Le score reste exact quelle que soit la langue
de réponse. **Aucune solution internationale ne fait cela pour la Guinée.**
C'est un levier majeur d'inclusion : il ouvre l'examen à des citoyens que
le tout-français exclut aujourd'hui.

### 4.2 Une traçabilité infalsifiable
Chaque événement sensible (résultat d'examen, paiement) est inscrit dans un
journal d'audit **inviolable** : les entrées sont chaînées
cryptographiquement, si bien que toute altération, insertion ou suppression
devient immédiatement détectable. En cas de contestation d'un résultat
devant la justice, l'État dispose d'une **preuve d'intégrité**.

### 4.3 Pensée pour le terrain guinéen
Mode hors-ligne pour l'entraînement (connectivité intermittente), moyens de
paiement locaux, interface mobile d'abord (la majorité des candidats sont
sur téléphone), documents officiels aux couleurs nationales.

---

## 5. Architecture technique

**Principe :** une architecture éprouvée, standard de l'industrie, sans
dépendance exotique — pour la pérennité et la facilité de maintenance.

- **Frontend** : application web moderne (React), installable sur mobile
  (PWA), fonctionnant même en connectivité faible.
- **Backend** : API robuste (FastAPI/Python), 164 points d'accès, contrôle
  d'accès par rôle (candidat, auto-école, agent de centre, admin, autorité
  DNTT).
- **Base de données** : PostgreSQL, migrations versionnées et
  rétrocompatibles.
- **Sécurité** : chiffrement en transit, en-têtes de sécurité, limitation de
  débit, validation stricte des secrets en production, journal d'audit
  inviolable.
- **Observabilité** : capture des erreurs en temps réel (Sentry),
  tableau de bord temps réel.
- **Industrialisation** : conteneurisation (Docker), intégration continue,
  sauvegarde automatisée et vérifiée.

---

## 6. Sécurité et conformité

- **Contrôle d'accès** : chaque rôle ne voit et ne fait que ce qui le
  concerne (vérifié par tests : un candidat ne peut ni accéder au tableau de
  bord, ni agir sur la réservation d'un autre).
- **Anti-fraude** : validation d'entrée par QR + code, détection d'anomalies
  de paiement, tableau de bord anti-fraude national.
- **Protection des données** : fonctions RGPD intégrées ; à compléter par la
  conformité à la réglementation guinéenne (APDP) via une analyse d'impact.
- **Traçabilité inviolable** : voir §4.2.
- **Recommandé avant le national** : audit de sécurité indépendant (test
  d'intrusion par un tiers), gestion des secrets par coffre-fort dédié.

---

## 7. Passage à l'échelle nationale

Le socle est prêt ; le national requiert un durcissement d'infrastructure,
documenté et chiffré.

**Capacité mesurée** : le code est efficace (peu de requêtes, aucune erreur
sous charge). La capacité totale dépend du dimensionnement de l'hébergement,
qui se multiplie avec le nombre de processus serveur.

**Dimensionnement recommandé par vague :**

| Vague | Périmètre | Infrastructure |
|---|---|---|
| 1 — Pilote | 1-3 centres Conakry | Plan de base, base par défaut |
| 2 — Régional | 10-20 centres | Plan renforcé, pool de connexions |
| 3 — National | 135 centres | Haute disponibilité, PgBouncer, cache Redis, CDN, sessions échelonnées |

**Haute disponibilité (national)** : plusieurs instances derrière un
répartiteur de charge, base répliquée avec bascule automatique, objectifs
de reprise chiffrés (RTO/RPO), stockage externe chiffré des sauvegardes.

---

## 8. Stratégie de déploiement recommandée

Nous recommandons formellement un déploiement **en trois vagues**, et non un
lancement national immédiat. Un État ne signe pas un contrat national sur
une promesse : il le signe sur un pilote qui a réussi.

1. **Pilote encadré** (1-3 centres, Conakry, 4-8 semaines) — prouver le
   service en conditions réelles avec un volume maîtrisé. Prérequis :
   questions validées par la DNTT, paiements réels testés, notifications
   actives.
2. **Extension régionale** (10-20 centres, 2-3 mois) — valider la montée en
   charge, la connectivité hors-Conakry, la formation des agents.
3. **Généralisation nationale** (135 centres) — uniquement après succès
   avéré des deux premières vagues.

Le pilote n'est pas une étape mineure : c'est la **preuve** qui justifie
l'engagement national.

---

## 9. Ce qui relève de la décision et de l'accompagnement de l'État

Au-delà du code, un déploiement national suppose :

- Un **mandat officiel** conférant valeur légale aux résultats.
- La **validation officielle des 200 questions** par la DNTT (l'outil est
  prêt ; la décision est métier).
- L'ouverture des **comptes marchands** Mobile Money auprès des opérateurs.
- La **conformité APDP** (données personnelles) via analyse d'impact.
- La **formation des agents** des centres et un **support de premier niveau**.
- Les **équipements** des centres (postes, connectivité, énergie) pour les
  zones rurales.
- Un **cadre de gouvernance et de maintenance** (séquestre du code, SLA,
  propriété des données).

DataSphere Innovation, acteur local, est positionné pour accompagner ces
dimensions dans la durée — un avantage décisif sur les prestataires
internationaux, plus coûteux, plus lents, et éloignés du terrain guinéen.

---

## 10. Conclusion

CodeRoute Guinée n'est pas un projet à démarrer : c'est une plateforme
construite, testée et documentée, prête pour un pilote encadré. Elle réunit
les garanties d'un système d'État (contenu certifié, paiement fiable,
données récupérables, tenue à l'échelle) et des différenciateurs uniques
(langues nationales, traçabilité inviolable) qu'aucune solution
internationale n'offre pour la Guinée.

Nous proposons à la DNTT d'engager la **première vague pilote**, dont le
succès fondera la décision de généralisation nationale.

---

*Références techniques disponibles : stratégie de sauvegarde
(`backup_restore.md`), configuration des paiements
(`mobile_money_production.md`), activation des notifications
(`notifications_activation.md`), analyse de charge (`load_testing.md`),
checklist de recette (`recette_production.md`).*
