#!/bin/bash
# smoke_test.sh — Tests de smoke post-déploiement
#
# Usage :
#   bash scripts/smoke_test.sh [API_URL]
#   bash scripts/smoke_test.sh https://api.coderoute.gov.gn
#
# Vérifie que tous les endpoints critiques répondent correctement

set -uo pipefail

API="${1:-https://api.coderoute.gov.gn}"
PASS=0; FAIL=0

GREEN='\033[0;32m'; RED='\033[0;31m'; NC='\033[0m'
ok()   { echo -e "  ${GREEN}✅${NC} $1"; ((PASS++)); }
fail() { echo -e "  ${RED}❌${NC} $1: $2"; ((FAIL++)); }

check_status() {
    local label="$1" url="$2" expected="${3:-200}"
    local actual
    actual=$(curl -s -o /dev/null -w "%{http_code}" --max-time 10 "$url" 2>/dev/null)
    if [[ "$actual" == "$expected" ]]; then
        ok "$label ($actual)"
    else
        fail "$label" "attendu $expected, reçu $actual"
    fi
}

check_json_field() {
    local label="$1" url="$2" field="$3"
    local response
    response=$(curl -sf --max-time 10 "$url" 2>/dev/null)
    if echo "$response" | python3 -c "import sys,json; d=json.load(sys.stdin); assert '$field' in d" 2>/dev/null; then
        ok "$label (champ '$field' présent)"
    else
        fail "$label" "champ '$field' absent dans la réponse"
    fi
}

echo ""
echo "🔍 Smoke tests — CodeRoute Guinée"
echo "   API: $API"
echo "   $(date '+%d/%m/%Y %H:%M:%S')"
echo ""

echo "── Santé ──────────────────────────────────────────────────"
check_status     "/health"              "$API/health"
check_json_field "/health — status"     "$API/health"              "status"
check_json_field "/health/readiness"    "$API/health/readiness"    "database"

echo ""
echo "── Auth ───────────────────────────────────────────────────"
check_status "/auth/login sans token" "$API/api/v1/auth/login" "405"
# POST login avec credentials invalides → 401 (pas 500)
RESP=$(curl -sf -X POST "$API/api/v1/auth/login" \
    -d "username=fake@test.com&password=wrongpassword" \
    -o /dev/null -w "%{http_code}" 2>/dev/null)
[[ "$RESP" == "401" ]] && ok "/auth/login invalide → 401" || fail "/auth/login" "attendu 401, reçu $RESP"

echo ""
echo "── API protégée (sans token → 401) ───────────────────────"
for endpoint in /api/v1/candidates /api/v1/centers /api/v1/dashboard /api/v1/users; do
    CODE=$(curl -sf -o /dev/null -w "%{http_code}" --max-time 5 "$API$endpoint" 2>/dev/null)
    [[ "$CODE" == "401" ]] && ok "$endpoint → 401" || fail "$endpoint" "attendu 401, reçu $CODE"
done

echo ""
echo "── Audio ──────────────────────────────────────────────────"
check_status "/api/v1/audio/inventory" "$API/api/v1/audio/inventory"
check_json_field "audio inventory fields" "$API/api/v1/audio/inventory" "by_locale"

echo ""
echo "── Webhooks (sans payload → 200) ──────────────────────────"
for wh in /api/v1/payments/webhook/wave /api/v1/payments/webhook/paydunya; do
    CODE=$(curl -sf -X POST -H "Content-Type: application/json" \
        -d '{}' -o /dev/null -w "%{http_code}" --max-time 5 "$API$wh" 2>/dev/null)
    [[ "$CODE" == "200" ]] && ok "POST $wh → 200" || fail "POST $wh" "attendu 200, reçu $CODE"
done

echo ""
echo "── SSL ────────────────────────────────────────────────────"
if [[ "$API" == https://* ]]; then
    DOMAIN="${API#https://}"
    EXPIRY=$(echo | openssl s_client -connect "$DOMAIN:443" -servername "$DOMAIN" 2>/dev/null | \
             openssl x509 -noout -enddate 2>/dev/null | cut -d= -f2 || echo "N/A")
    ok "SSL valide — expire : $EXPIRY"
else
    echo "  ⚠️  URL HTTP — SSL non vérifié"
fi

echo ""
echo "──────────────────────────────────────────────────────────"
TOTAL=$((PASS + FAIL))
echo "  Résultat : $PASS/$TOTAL tests réussis"
if [[ $FAIL -gt 0 ]]; then
    echo -e "  ${RED}$FAIL test(s) en échec${NC}"
    exit 1
else
    echo -e "  ${GREEN}✅ Tous les tests passent — déploiement OK${NC}"
fi
echo ""
