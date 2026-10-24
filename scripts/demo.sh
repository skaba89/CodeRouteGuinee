#!/usr/bin/env bash
# demo.sh — pilote l'environnement local de démonstration DNTT (voir DEMO.md).
#
#   scripts/demo.sh init            génère .env.demo (clés aléatoires, non versionné)
#   scripts/demo.sh up              construit et démarre la stack de démo
#   scripts/demo.sh seed [MIN]      données de démo + session live dans MIN minutes (défaut 15)
#   scripts/demo.sh live [MIN]      ajoute seulement une nouvelle session live
#   scripts/demo.sh check           répétition automatique du parcours candidat complet
#   scripts/demo.sh tamper          falsifie EN BASE un résultat ajourné (démo anti-fraude)
#   scripts/demo.sh restore         rétablit la valeur d'origine falsifiée par tamper
#   scripts/demo.sh down            arrête la stack (données conservées)
#   scripts/demo.sh wipe            supprime la base de démo (confirmation demandée)
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PROJECT="coderoute-demo"
COMPOSE=(docker compose -p "$PROJECT" --project-directory "$ROOT"
         -f "$ROOT/docker-compose.yml" -f "$ROOT/docker-compose.demo.yml"
         --env-file "$ROOT/.env" --env-file "$ROOT/.env.demo")
PSQL=(docker exec -i coderoute-postgres psql -U coderoute -d coderoute -tA -v ON_ERROR_STOP=1)
TAMPER_FILE="$ROOT/.demo-tamper"

require_env() {
  [ -f "$ROOT/.env" ] || { echo "❌ .env absent : cp .env.dev .env"; exit 1; }
  [ -f "$ROOT/.env.demo" ] || { echo "❌ .env.demo absent : scripts/demo.sh init"; exit 1; }
}

random_key() { python3 -c 'import secrets; print(secrets.token_urlsafe(48))'; }

cmd="${1:-help}"
case "$cmd" in
  init)
    if [ -f "$ROOT/.env.demo" ]; then
      echo "✅ .env.demo existe déjà (conservé : la chaîne d'audit dépend de sa clé)."
      exit 0
    fi
    umask 077
    {
      echo "# Généré par scripts/demo.sh init — ne pas versionner."
      echo "AUDIT_CHAIN_HMAC_KEY=$(random_key)"
      echo "ADMIN_REGISTRATION_TOKEN=$(random_key)"
    } > "$ROOT/.env.demo"
    echo "✅ .env.demo créé."
    ;;
  up)
    require_env
    "${COMPOSE[@]}" up -d --build --wait backend frontend
    echo "✅ Frontend http://localhost:5173 — API http://localhost:8000/docs"
    ;;
  seed)
    require_env
    docker exec coderoute-backend python -m app.seed_demo_dntt --live-in "${2:-15}"
    ;;
  live)
    require_env
    docker exec coderoute-backend python -m app.seed_demo_dntt --live-only --live-in "${2:-15}"
    ;;
  check)
    require_env
    docker cp "$ROOT/scripts/demo_rehearsal.py" coderoute-backend:/tmp/demo_rehearsal.py
    docker exec coderoute-backend python /tmp/demo_rehearsal.py
    ;;
  tamper)
    # Simule un agent qui modifie directement la base pour transformer un
    # ajournement en admission. La valeur d'origine est conservée pour restore.
    [ -f "$TAMPER_FILE" ] && { echo "❌ Falsification déjà en cours : scripts/demo.sh restore"; exit 1; }
    row=$("${PSQL[@]}" -c "select seq || '|' || details::text from audit_logs
      where action = 'exam.submitted' and details->>'passed' = 'false' and seq is not null
      order by seq limit 1")
    [ -n "$row" ] || { echo "❌ Aucun résultat ajourné chaîné à falsifier."; exit 1; }
    printf '%s' "$row" > "$TAMPER_FILE"
    seq="${row%%|*}"
    "${PSQL[@]}" -c "update audit_logs set details = (details::jsonb
      || '{\"score\": 38, \"passed\": true}'::jsonb)::json where seq = $seq" >/dev/null
    echo "⚠️  Entrée n°$seq falsifiée en base (score → 38, admis). Vérifier l'intégrité dans Administration › Audit."
    ;;
  restore)
    [ -f "$TAMPER_FILE" ] || { echo "Rien à restaurer."; exit 0; }
    row="$(cat "$TAMPER_FILE")"
    seq="${row%%|*}"
    original="${row#*|}"
    # Variable psql via stdin (l'interpolation :'var' ne s'applique pas à -c).
    echo "update audit_logs set details = :'original'::json where seq = $seq;" \
      | "${PSQL[@]}" -v original="$original" >/dev/null
    rm -f "$TAMPER_FILE"
    echo "✅ Entrée n°$seq restaurée."
    ;;
  down)
    require_env
    "${COMPOSE[@]}" down
    ;;
  wipe)
    require_env
    read -r -p "Supprimer définitivement la base de démo ($PROJECT) ? [oui/N] " answer
    [ "$answer" = "oui" ] || { echo "Annulé."; exit 1; }
    "${COMPOSE[@]}" down -v
    ;;
  *)
    sed -n '2,13p' "$0"
    ;;
esac
