# Protection GitHub de `main`

Cette procédure traite le P0 suivi dans l'issue #231. Elle ne doit être considérée comme terminée que lorsque le Ruleset est **réellement actif** dans GitHub et que son comportement est vérifié.

## Politique cible

Le Ruleset `protect-main-release-preflight` cible uniquement `refs/heads/main` et impose :

- changements via Pull Request ;
- check GitHub `release-preflight` obligatoire ;
- branche de PR à jour avec `main` avant merge (`strict_required_status_checks_policy=true`) ;
- suppression de `main` interdite ;
- force-push interdit ;
- aucun bypass acteur implicite ;
- aucun reviewer indépendant obligatoire, afin de ne pas bloquer un dépôt maintenu par une seule personne.

Le check `release-preflight` est le gate agrégé de la CI existante : il ne devient vert qu'après les tests backend, la couverture, le build frontend, les tests UI et le preflight de production.

## Pré-requis administrateur

Utiliser un token GitHub à durée courte disposant de la permission dépôt **Administration: write**. Ne jamais committer ce token ni l'ajouter dans un fichier `.env` suivi par Git.

Sous Bash :

```bash
export GITHUB_ADMIN_TOKEN='<token-temporaire>'
python scripts/apply_github_main_ruleset.py --dry-run
python scripts/apply_github_main_ruleset.py --apply
python scripts/apply_github_main_ruleset.py --check-only
unset GITHUB_ADMIN_TOKEN
```

Sous PowerShell :

```powershell
$env:GITHUB_ADMIN_TOKEN = '<token-temporaire>'
python scripts/apply_github_main_ruleset.py --dry-run
python scripts/apply_github_main_ruleset.py --apply
python scripts/apply_github_main_ruleset.py --check-only
Remove-Item Env:GITHUB_ADMIN_TOKEN
```

Le script est idempotent : il crée le Ruleset s'il n'existe pas, sinon il met à jour le Ruleset du même nom, puis relit GitHub et vérifie la configuration effective.

## Vérification dans GitHub

Après `--apply` :

1. ouvrir **Repository → Settings → Rules → Rulesets** ;
2. vérifier que `protect-main-release-preflight` est **Active** ;
3. vérifier que la cible est `main` ;
4. vérifier **Require a pull request before merging** ;
5. vérifier **Require status checks to pass** avec `release-preflight` ;
6. vérifier **Require branches to be up to date before merging** ;
7. vérifier que la suppression et les force-push sont bloqués ;
8. vérifier qu'aucun bypass permanent non documenté n'existe.

## Preuve négative avant fermeture de #231

La configuration seule n'est pas une preuve suffisante. Effectuer au minimum ces tests avec un compte ayant normalement accès en écriture :

- tentative de push direct vers `main` → **refusée** ;
- tentative de force-push vers `main` → **refusée** ;
- PR dont `release-preflight` est rouge ou absent → merge **refusé** ;
- PR en retard sur `main` → merge **refusé** tant qu'elle n'est pas remise à jour ;
- PR à jour avec `release-preflight` vert → merge autorisé selon la politique.

Conserver les Rule Insights / rule suites correspondants comme preuve d'exploitation.

## Override d'urgence

La configuration livrée ne définit **aucun bypass**. Si un bypass d'urgence est ajouté ultérieurement :

- le limiter à un acteur explicitement nommé ;
- préférer un bypass PR plutôt qu'un bypass permanent lorsque possible ;
- documenter le motif, l'approbateur et la période d'activation ;
- retirer le bypass immédiatement après l'incident ;
- relancer `--check-only` : il doit volontairement échouer tant qu'un bypass non conforme est présent.

L'issue #231 ne doit être fermée qu'après preuve que GitHub applique effectivement ces règles à `main`.
