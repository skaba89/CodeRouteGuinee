# Imports de donnees officielles

Ce document decrit les formats acceptes pour remplacer progressivement les donnees de demonstration par des donnees institutionnelles.

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

- `code` est normalise en majuscules et sert de cle d'upsert.
- un code deja existant met le centre a jour;
- un code nouveau cree le centre;
- un doublon dans le meme lot bloque l'import;
- le lot est limite a 500 centres;
- chaque import est journalise dans `audit_logs` avec source, motif, volumes et codes.

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
- Importer d'abord en staging.
- Verifier le journal d'audit apres import.
- Exporter le dashboard et le rapport institutionnel PDF apres validation.
