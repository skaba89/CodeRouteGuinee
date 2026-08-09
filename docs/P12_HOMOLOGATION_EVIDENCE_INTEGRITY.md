# P12 — Intégrité des pièces d’homologation DNTT

## Objectif

Les cinq pièces obligatoires du dossier P12 ne doivent pas être de simples références textuelles. CodeRoute exige désormais pour chaque pièce :

- un code de preuve institutionnel connu ;
- une référence GED **interne** ;
- la date d’émission de la pièce ;
- l’empreinte SHA-256 du document archivé ;
- l’acteur et l’heure de rattachement.

CodeRoute ne stocke pas le fichier institutionnel lui-même dans ce workflow. Le document source reste dans la GED/coffre de preuves de l’autorité compétente.

## Les cinq pièces obligatoires

1. `dntt_exam_rules` — règles officielles DNTT ;
2. `legal_review` — revue juridique ;
3. `security_assessment` — évaluation sécurité ;
4. `operations_readiness` — validation exploitation/PRA ;
5. `content_signoff` — validation des contenus et droits médias.

## Contrat d’une preuve

Exemple :

```json
{
  "code": "legal_review",
  "reference": "GED-DNTT-LEGAL-2026-001",
  "artifact_sha256": "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
  "issued_at": "2026-08-09T18:00:00+00:00",
  "note": "Avis juridique signé et archivé dans la GED institutionnelle."
}
```

### Garde-fous

- `artifact_sha256` : exactement 64 caractères hexadécimaux ;
- `reference` : identifiant interne, pas d’URL et pas de credential ;
- `issued_at` : une date future au-delà de 5 minutes de tolérance est refusée ;
- une pièce remplacée avant soumission conserve l’ancienne référence/hash dans `evidence_history` ;
- après soumission, les preuves ne sont plus modifiables par ce workflow.

## Soumission

Avant `POST /homologation-dossiers/{reference}/submit`, le backend revalide les cinq pièces :

- présence des cinq codes ;
- référence interne valide ;
- SHA-256 présent et valide ;
- date d’émission lisible et non future.

Un dossier historique contenant des preuves sans SHA est donc bloqué avec :

`HOMOLOGATION_EVIDENCE_INTEGRITY_INVALID`

Il doit repasser en préparation/migration contrôlée avant de pouvoir être utilisé pour une homologation nationale.

### Migration des dossiers historiques

La lecture des anciens dossiers reste compatible : une ancienne référence sans `artifact_sha256` n’est ni supprimée ni interprétée comme une preuve valide. Dans le dashboard, elle apparaît **« À re-hasher »** et n’entre pas dans le compteur `5/5 hashées`.

Tant que le dossier est encore en `draft` ou `evidence_review`, l’opérateur peut sélectionner le même type de preuve et rattacher la pièce GED correspondante avec son SHA-256. L’ancienne référence est conservée dans `evidence_history`. Un dossier déjà avancé dans le workflow doit faire l’objet d’une migration/reprise contrôlée plutôt que d’une modification silencieuse de ses pièces.

## Décision finale

Lors d’une décision positive, l’intégrité des cinq pièces est revalidée avant la logique P12 existante :

- politique toujours active ;
- même `policy_sha256` ;
- readiness toujours verte ;
- deux approbations distinctes ;
- décision finale réservée au `super_admin`.

Une décision de rejet reste possible même si l’intégrité d’une pièce est dégradée : l’autorité doit pouvoir clôturer un dossier non conforme sans le présenter comme homologué.

## Interface

Le dashboard national expose un panneau « Dossier de preuves — homologation DNTT » permettant :

- de sélectionner un dossier ;
- d’identifier visuellement les pièces manquantes, hashées ou héritées sans hash ;
- de rattacher ou remplacer une pièce avant soumission ;
- de soumettre les cinq preuves ;
- de réaliser les deux approbations selon RBAC ;
- de prendre la décision finale en `super_admin`.

Le SHA complet reste disponible dans le dossier ; l’interface n’affiche qu’un préfixe pour la lisibilité.

## Vérification de la pièce externe

Avant rattachement :

Linux/macOS :

```bash
sha256sum document.pdf
```

PowerShell :

```powershell
Get-FileHash .\document.pdf -Algorithm SHA256
```

L’empreinte saisie dans CodeRoute doit être identique à celle de la pièce conservée dans la GED.

## Limite institutionnelle

Un SHA-256 prouve l’identité binaire d’une pièce, **pas** sa valeur juridique. Le système ne déduit jamais qu’un document est signé, juridiquement valable ou approuvé par la DNTT sur la seule présence d’un hash.

L’issue #140 reste ouverte jusqu’à la collecte des vraies pièces, des approbations et de la décision institutionnelle.