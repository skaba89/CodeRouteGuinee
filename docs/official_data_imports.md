# Imports de donnees officielles

Ce document decrit les formats acceptes pour remplacer progressivement les donnees de demonstration par des donnees institutionnelles.

## Candidats officiels

Endpoint protege:

```text
POST /api/v1/candidates/import-official
```

Roles autorises:

- `admin`
- `super_admin`

Payload JSON:

```json
{
  "source": "Registre national pilote",
  "reason": "Chargement candidats pilotes",
  "dry_run": true,
  "candidates": [
    {
      "first_name": "Mamadou",
      "last_name": "Diallo",
      "identity_number": "GN-ID-2026-0001",
      "phone": "+224620000001",
      "permit_category": "B",
      "status": "registered"
    }
  ]
}
```

Regles:

- `dry_run: true` valide le fichier et retourne les compteurs sans ecrire en base;
- `identity_number` est normalise en majuscules et sert de cle d'upsert;
- un identifiant deja existant met le dossier candidat a jour;
- un identifiant nouveau cree un dossier avec reference `GN-CODE-...`;
- un doublon dans le meme lot bloque l'import;
- le lot est limite a 1000 candidats;
- chaque import reel est journalise dans `audit_logs`.

Format CSV accepte dans l'interface admin:

```text
prenom;nom;numero_identite;telephone;categorie_permis;statut
Mamadou;Diallo;GN-ID-2026-0001;+224620000001;B;registered
```

Statuts acceptes:

- `registered`
- `verified`
- `suspended`

## Centres agrees

Endpoint protege:

```text
POST /api/v1/centers/import-official
```

Roles autorises:

- `admin`
- `super_admin`

Payload JSON:

```json
{
  "source": "Liste officielle DNTT",
  "reason": "Chargement des centres pilotes",
  "dry_run": true,
  "centers": [
    {
      "code": "CRG-CONAKRY-001",
      "name": "Centre officiel Conakry",
      "city": "Conakry",
      "address": "Kaloum",
      "capacity": 30,
      "status": "accredited"
    }
  ]
}
```

Regles:

- `dry_run: true` valide le fichier et retourne les compteurs sans ecrire en base;
- `code` est normalise en majuscules et sert de cle d'upsert.
- un code deja existant met le centre a jour;
- un code nouveau cree le centre;
- un doublon dans le meme lot bloque l'import;
- le lot est limite a 500 centres;
- chaque import reel est journalise dans `audit_logs` avec source, motif, volumes et codes.

Format CSV accepte dans l'interface admin:

```text
code;nom;ville;adresse;capacite;statut
CRG-CONAKRY-001;Centre officiel Conakry;Conakry;Kaloum;30;accredited
CRG-KINDIA-001;Centre officiel Kindia;Kindia;Centre ville;24;pending_audit
```

Statuts acceptes:

- `pending_audit`
- `active`
- `accredited`
- `suspended`

## Controle avant import

- Verifier la source officielle du fichier.
- Conserver une copie du fichier transmis.
- Lancer d'abord une simulation (`dry_run: true`) depuis l'API ou l'interface admin.
- Importer ensuite en staging avec `dry_run: false`.
- Verifier le journal d'audit apres import.
- Exporter le dashboard et le rapport institutionnel PDF apres validation.

Dans l'interface admin, la case `Simulation sans ecriture` est cochee par defaut pour les imports candidats, centres, paiements et questions. Decochez-la uniquement apres validation des compteurs affiches.

## Paiements operateur

Endpoint protege:

```text
POST /api/v1/payments/admin/import-official
```

Roles autorises:

- `admin`
- `super_admin`

Payload JSON:

```json
{
  "source": "Orange Money",
  "reason": "Rapprochement quotidien",
  "dry_run": true,
  "payments": [
    {
      "booking_reference": "GN-BOOK-2026-000001",
      "amount_gnf": 250000,
      "provider": "orange_money",
      "phone": "+224620000001",
      "status": "paid",
      "receipt_number": "OM-RECU-000001",
      "created_at": "2026-06-18T10:30:00"
    }
  ]
}
```

Regles:

- `dry_run: true` valide le fichier et retourne les compteurs sans ecrire en base;
- `receipt_number` est normalise en majuscules et sert de cle d'upsert;
- la reservation doit exister dans CodeRoute avant import;
- un recu deja existant met le paiement a jour;
- un recu nouveau cree un paiement rapproche;
- un doublon dans le meme lot bloque l'import;
- le lot est limite a 1000 paiements;
- chaque import reel est journalise dans `audit_logs`.

Format CSV accepte dans l'interface admin:

```text
reference_reservation;montant;operateur;telephone;statut;numero_recu;date_iso_optionnelle
GN-BOOK-2026-000001;250000;orange_money;+224620000001;paid;OM-RECU-000001;2026-06-18T10:30:00
```

## Questions officielles

Endpoint protege:

```text
POST /api/v1/questions/import-official
```

Roles autorises:

- `admin`
- `super_admin`

Payload JSON:

```json
{
  "source": "Commission nationale du code",
  "reason": "Chargement banque pilote",
  "dry_run": true,
  "questions": [
    {
      "category": "signalisation",
      "text": "Que signifie un feu rouge fixe ?",
      "options": ["S arreter", "Passer avec prudence", "Accelerer"],
      "correct_answer": "S arreter",
      "explanation": "Le feu rouge impose l arret.",
      "is_active": true
    }
  ]
}
```

Regles:

- `dry_run: true` valide le fichier et retourne les compteurs sans ecrire en base;
- la cle d'upsert est `category + text` normalisee;
- la bonne reponse doit etre presente dans `options`;
- un doublon dans le meme lot bloque l'import;
- le lot est limite a 1000 questions;
- chaque import reel est journalise dans `audit_logs`;
- les questions inactives restent visibles dans la gouvernance admin, mais pas dans l'examen public.

Format CSV accepte dans l'interface admin:

```text
categorie;question;option1|option2|option3;bonne_reponse;explication;active
signalisation;Que signifie un feu rouge fixe ?;S arreter|Passer avec prudence|Accelerer;S arreter;Le feu rouge impose l arret.;true
```
