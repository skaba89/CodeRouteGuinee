# SECURITY_ROTATION.md — CodeRoute Guinée

## ⚠️ Action requise : rotation des anciens secrets

Des secrets ont été accidentellement commités dans le dépôt Git lors des sessions
de débogage en juillet 2026. Ils sont désormais retirés du code source (commit `harden-render-config-and-fix-auth-routing`).

### Secrets à révoquer immédiatement

| Secret | Action |
|--------|--------|
| Mot de passe Neon `npg_yG8BsXx7VAQo` | Render Dashboard → reset password Neon |
| SECRET_KEY `4b11230abf...` | Générer une nouvelle clé dans Render |
| CSRF_SECRET `82c96b1a...` | Générer une nouvelle clé dans Render |
| Mot de passe admin `CodeRoute2026!` | Changer via "Mon compte" dans l'UI |

### Procédure de rotation

1. **Neon PostgreSQL** : console.neon.tech → Reset password → copier la nouvelle URL
2. **Render Dashboard** → `coderoute-backend` → Environment :
   - Supprimer `SECRET_KEY` (laisser Render regénérer via `generateValue`)
   - Supprimer `CSRF_SECRET` (idem)
   - Mettre à jour `DATABASE_URL` et `ALEMBIC_DATABASE_URL` avec les nouvelles URLs Neon
3. **Manual Deploy** du backend
4. Se connecter avec le nouvel admin et changer le mot de passe

### Après rotation

- Tous les tokens JWT existants seront invalidés (reconnexion requise)
- Tester le login depuis `coderouteguinee-frontend.onrender.com`

### Bonne pratique

Ne jamais mettre de secrets dans :
- `config.py` (même en "valeurs par défaut")
- `render.yaml` (utiliser `sync: false` ou `generateValue: true`)
- `entrypoint.sh` (utiliser les variables d'environnement)
- les migrations Alembic (pas de hash de mot de passe)
