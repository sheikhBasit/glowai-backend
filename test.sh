#!/usr/bin/env bash
# GlowAI API — full curl test suite
# Usage: ./test.sh [BASE_URL]
# Default BASE_URL: http://localhost:8000

set -e
BASE="${1:-http://localhost:8000}"
EMAIL="testuser_$$@glowai.com"
PASS="TestPass123!"
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

ok()   { echo -e "${GREEN}  PASS${NC} $1"; }
fail() { echo -e "${RED}  FAIL${NC} $1 — $2"; }
info() { echo -e "${YELLOW}──${NC} $1"; }

assert_field() {
  local label="$1" json="$2" field="$3"
  if echo "$json" | python3 -c "import sys,json; d=json.load(sys.stdin); assert '$field' in d" 2>/dev/null; then
    ok "$label"
  else
    fail "$label" "missing field '$field' in: ${json:0:120}"
  fi
}

assert_status() {
  local label="$1" got="$2" want="$3"
  if [ "$got" = "$want" ]; then ok "$label"
  else fail "$label" "expected HTTP $want, got $got"; fi
}

# ── 0. Health ─────────────────────────────────────────────────────────────────
info "0. Health"
R=$(curl -s "$BASE/health")
assert_field "GET /health" "$R" "status"
echo "     $(echo $R | python3 -c "import sys,json; d=json.load(sys.stdin); print('vision:', d.get('vision'), '| replicate:', d.get('replicate'), '| groq:', d.get('groq'), '| gemini:', d.get('gemini'))")"

# ── 1. Auth ───────────────────────────────────────────────────────────────────
info "1. Auth"

# Signup
R=$(curl -s -w "\n%{http_code}" -X POST "$BASE/auth/signup" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$EMAIL\",\"password\":\"$PASS\",\"name\":\"Test User\"}")
HTTP=$(echo "$R" | tail -1); BODY=$(echo "$R" | head -1)
assert_status "POST /auth/signup" "$HTTP" "201"
assert_field  "  → has access_token" "$BODY" "access_token"
TOKEN=$(echo "$BODY" | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")
REFRESH=$(echo "$BODY" | python3 -c "import sys,json; print(json.load(sys.stdin)['refresh_token'])")
AUTH="Authorization: Bearer $TOKEN"

# Duplicate signup
HTTP=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$BASE/auth/signup" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$EMAIL\",\"password\":\"$PASS\"}")
assert_status "POST /auth/signup (duplicate → 409)" "$HTTP" "409"

# Login
R=$(curl -s -X POST "$BASE/auth/login" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$EMAIL\",\"password\":\"$PASS\"}")
assert_field "POST /auth/login" "$R" "access_token"

# Wrong password
HTTP=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$BASE/auth/login" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$EMAIL\",\"password\":\"wrong\"}")
assert_status "POST /auth/login (bad pass → 401)" "$HTTP" "401"

# Me
R=$(curl -s "$BASE/auth/me" -H "$AUTH")
assert_field "GET /auth/me" "$R" "email"

# Refresh
R=$(curl -s -X POST "$BASE/auth/refresh" \
  -H "Content-Type: application/json" \
  -d "{\"refresh_token\":\"$REFRESH\"}")
assert_field "POST /auth/refresh" "$R" "access_token"

# Bad token
HTTP=$(curl -s -o /dev/null -w "%{http_code}" "$BASE/auth/me" -H "Authorization: Bearer badtoken")
assert_status "GET /auth/me (bad token → 401)" "$HTTP" "401"

# Logout (revokes all tokens for this user) then re-login
HTTP=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$BASE/auth/logout" -H "$AUTH")
assert_status "POST /auth/logout" "$HTTP" "204"
HTTP=$(curl -s -o /dev/null -w "%{http_code}" "$BASE/auth/me" -H "$AUTH")
assert_status "  → revoked token rejected (401)" "$HTTP" "401"
# Re-login to get a fresh token for the rest of the tests
R=$(curl -s -X POST "$BASE/auth/login" -H "Content-Type: application/json" \
  -d "{\"email\":\"$EMAIL\",\"password\":\"$PASS\"}")
TOKEN=$(echo "$R" | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")
REFRESH=$(echo "$R" | python3 -c "import sys,json; print(json.load(sys.stdin)['refresh_token'])")
AUTH="Authorization: Bearer $TOKEN"
ok "  → re-login after logout"

# ── 2. Profile ────────────────────────────────────────────────────────────────
info "2. Profile"

R=$(curl -s "$BASE/profile" -H "$AUTH")
assert_field "GET /profile (auto-create)" "$R" "user_id"

R=$(curl -s -X PUT "$BASE/profile" -H "$AUTH" -H "Content-Type: application/json" \
  -d '{"skin_tone":"medium","skin_type":"combination","undertone":"warm","concerns":["acne","pigmentation"]}')
assert_field "PUT /profile" "$R" "skin_tone"
echo "     skin_tone: $(echo $R | python3 -c "import sys,json; print(json.load(sys.stdin)['skin_tone'])")"

# ── 3. Looks ──────────────────────────────────────────────────────────────────
info "3. Looks"

R=$(curl -s -w "\n%{http_code}" -X POST "$BASE/looks" -H "$AUTH" \
  -H "Content-Type: application/json" \
  -d '{"name":"Rose Romance","palette":{"lips":"#C0392B","blush":"#F48FB1","eyes":"#B76E79"},"zones":["lips","blush","eyes"],"occasion":"Date Night"}')
HTTP=$(echo "$R" | tail -1); BODY=$(echo "$R" | head -1)
assert_status "POST /looks" "$HTTP" "201"
assert_field  "  → has id" "$BODY" "id"
LOOK_ID=$(echo "$BODY" | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")

R=$(curl -s "$BASE/looks" -H "$AUTH")
COUNT=$(echo $R | python3 -c "import sys,json; print(len(json.load(sys.stdin)))")
ok "GET /looks ($COUNT look(s) found)"

R=$(curl -s "$BASE/looks/$LOOK_ID" -H "$AUTH")
assert_field "GET /looks/:id" "$R" "name"

# Score patch (no AI needed)
R=$(curl -s -X PATCH "$BASE/looks/$LOOK_ID/score" -H "$AUTH" \
  -H "Content-Type: application/json" \
  -d '{"overall":8.5,"color_harmony":9.0,"skin_match":7.5,"occasion_match":8.0,"vibe":"Romantic glam","tip":"Add a touch more blush","recommendation":"Try MAC Ruby Woo"}')
assert_field "PATCH /looks/:id/score" "$R" "score"

# ── 4. Diary ──────────────────────────────────────────────────────────────────
info "4. Diary"

R=$(curl -s -w "\n%{http_code}" -X POST "$BASE/diary" -H "$AUTH" \
  -F "title=My first entry" \
  -F "content=Tried the rose palette, looked amazing!" \
  -F "occasion=Date Night")
HTTP=$(echo "$R" | tail -1); BODY=$(echo "$R" | head -1)
assert_status "POST /diary" "$HTTP" "201"
assert_field  "  → has id" "$BODY" "id"
DIARY_ID=$(echo "$BODY" | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")

R=$(curl -s "$BASE/diary" -H "$AUTH")
COUNT=$(echo $R | python3 -c "import sys,json; print(len(json.load(sys.stdin)))")
ok "GET /diary ($COUNT entry/entries found)"

R=$(curl -s "$BASE/diary/$DIARY_ID" -H "$AUTH")
assert_field "GET /diary/:id" "$R" "title"

R=$(curl -s -X PUT "$BASE/diary/$DIARY_ID" -H "$AUTH" \
  -H "Content-Type: application/json" \
  -d '{"title":"Updated title","content":"Updated content"}')
assert_field "PUT /diary/:id" "$R" "title"

# ── 5. Scans ──────────────────────────────────────────────────────────────────
info "5. Scans"

R=$(curl -s "$BASE/scans" -H "$AUTH")
ok "GET /scans ($(echo $R | python3 -c "import sys,json; print(len(json.load(sys.stdin)))") report(s))"

R=$(curl -s "$BASE/scans?scan_type=face" -H "$AUTH")
ok "GET /scans?scan_type=face ($(echo $R | python3 -c "import sys,json; print(len(json.load(sys.stdin)))") face scan(s))"

# ── 6.5 Tutorials ─────────────────────────────────────────────────────────────
info "6.5 Tutorials"

R=$(curl -s "$BASE/tutorials" -H "$AUTH")
COUNT=$(echo $R | python3 -c "import sys,json; print(len(json.load(sys.stdin)))")
if [ "$COUNT" -gt "0" ]; then
  ok "GET /tutorials ($COUNT tutorials)"
else
  fail "GET /tutorials" "empty — run: venv/bin/python3 seed_tutorials.py"
fi

R=$(curl -s "$BASE/tutorials?category=lips" -H "$AUTH")
COUNT=$(echo $R | python3 -c "import sys,json; print(len(json.load(sys.stdin)))")
ok "GET /tutorials?category=lips ($COUNT results)"

R=$(curl -s "$BASE/tutorials?difficulty=beginner" -H "$AUTH")
COUNT=$(echo $R | python3 -c "import sys,json; print(len(json.load(sys.stdin)))")
ok "GET /tutorials?difficulty=beginner ($COUNT results)"

TUT_ID=$(curl -s "$BASE/tutorials" -H "$AUTH" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d[0]['id']) if d else print('')")
if [ -n "$TUT_ID" ]; then
  R=$(curl -s "$BASE/tutorials/$TUT_ID" -H "$AUTH")
  assert_field "GET /tutorials/:id" "$R" "video_url"
  echo "     $(echo $R | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['title'], '→', d['video_url'])")"
fi

# ── 6.8 Glow Journey ──────────────────────────────────────────────────────────
info "6.8 Glow Journey"

R=$(curl -s "$BASE/glow-journey" -H "$AUTH")
assert_field "GET /glow-journey" "$R" "stats"
echo "     looks: $(echo $R | python3 -c "import sys,json; print(json.load(sys.stdin)['stats']['total_looks'])") | streak: $(echo $R | python3 -c "import sys,json; print(json.load(sys.stdin)['stats']['activity_streak_days'])") day(s)"

# ── 6. AI endpoints (only if keys are set) ────────────────────────────────────
info "6. AI endpoints"

HAS_VISION=$(curl -s "$BASE/health" | python3 -c "import sys,json; print(json.load(sys.stdin).get('vision','none'))")
HAS_GROQ=$(curl -s "$BASE/health" | python3 -c "import sys,json; print(json.load(sys.stdin).get('groq',False))")

if [ "$HAS_VISION" = "none" ]; then
  echo -e "${YELLOW}  SKIP${NC} /score, /scan, /nail-scan — set GOOGLE_API_KEY or GROQ_API_KEY to test"
else
  # Create a tiny 1x1 white JPEG for testing
  TINY_JPEG=$(python3 -c "
import base64, io
from PIL import Image
img = Image.new('RGB', (64, 64), color=(200, 160, 140))
buf = io.BytesIO()
img.save(buf, format='JPEG')
print(base64.b64encode(buf.getvalue()).decode())
")
  HTTP=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$BASE/score" -H "$AUTH" \
    -H "Content-Type: application/json" \
    -d "{\"photo_base64\":\"$TINY_JPEG\",\"occasion\":\"Date Night\",\"makeup\":{\"lips\":\"#C0392B\"}}")
  assert_status "POST /score" "$HTTP" "200"

  HTTP=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$BASE/scan" -H "$AUTH" \
    -H "Content-Type: application/json" \
    -d "{\"photo_base64\":\"$TINY_JPEG\"}")
  assert_status "POST /scan" "$HTTP" "201"

  HTTP=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$BASE/nail-scan" -H "$AUTH" \
    -H "Content-Type: application/json" \
    -d "{\"photo_base64\":\"$TINY_JPEG\"}")
  assert_status "POST /nail-scan" "$HTTP" "201"
fi

if [ "$HAS_GROQ" = "True" ]; then
  R=$(curl -s "$BASE/recommendations?occasion=Date+Night" -H "$AUTH")
  assert_field "GET /recommendations" "$R" "palettes"
else
  echo -e "${YELLOW}  SKIP${NC} /recommendations — set GROQ_API_KEY to test"
fi

# ── 7. Routine ────────────────────────────────────────────────────────────────
info "7. Routine"

R=$(curl -s "$BASE/routine" -H "$AUTH")
assert_field "GET /routine (empty)" "$R" "morning"

R=$(curl -s -X PUT "$BASE/routine" -H "$AUTH" -H "Content-Type: application/json" -d '{
  "morning": [{"step":"Cleanse","product":"CeraVe","duration_min":2},{"step":"SPF","product":"La Roche Posay","duration_min":1}],
  "evening": [{"step":"Oil cleanser","product":"DHC","duration_min":3},{"step":"Retinol","product":"Olay","duration_min":1}],
  "weekly":  [{"step":"Exfoliate","product":"Pixi Glow Tonic","duration_min":5}],
  "notes": "Always patch test new products"
}')
assert_field "PUT /routine" "$R" "updated_at"
STEPS=$(echo $R | python3 -c "import sys,json; print(len(json.load(sys.stdin)['morning']))")
ok "  → $STEPS morning steps saved"

R=$(curl -s "$BASE/routine" -H "$AUTH")
NOTE=$(echo $R | python3 -c "import sys,json; print(json.load(sys.stdin).get('notes',''))")
ok "GET /routine (persisted — notes: $NOTE)"

# ── 7.5 Account management ────────────────────────────────────────────────────
info "7.5 Account"

R=$(curl -s -X PATCH "$BASE/account/name" -H "$AUTH" -H "Content-Type: application/json" \
  -d '{"name":"Glow Queen"}')
assert_field "PATCH /account/name" "$R" "name"
echo "     name: $(echo $R | python3 -c "import sys,json; print(json.load(sys.stdin)['name'])")"

HTTP=$(curl -s -o /dev/null -w "%{http_code}" -X PATCH "$BASE/account/password" -H "$AUTH" \
  -H "Content-Type: application/json" \
  -d "{\"current_password\":\"$PASS\",\"new_password\":\"NewPass456!\"}")
assert_status "PATCH /account/password" "$HTTP" "204"
PASS="NewPass456!"  # update for subsequent tests

# Re-login with new password to get fresh token
R=$(curl -s -X POST "$BASE/auth/login" -H "Content-Type: application/json" \
  -d "{\"email\":\"$EMAIL\",\"password\":\"$PASS\"}")
TOKEN=$(echo "$R" | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")
AUTH="Authorization: Bearer $TOKEN"
ok "  → re-login with new password"

# ── 7.8 FLUX generate (skipped — needs Replicate + real image) ────────────────
info "7.8 FLUX /generate"
echo -e "${YELLOW}  SKIP${NC} POST /generate — needs real face image + lip mask (test in app)"

# ── 8. Cleanup — delete test diary + look, then account ──────────────────────
info "8. Cleanup"

HTTP=$(curl -s -o /dev/null -w "%{http_code}" -X DELETE "$BASE/diary/$DIARY_ID" -H "$AUTH")
assert_status "DELETE /diary/:id" "$HTTP" "204"

HTTP=$(curl -s -o /dev/null -w "%{http_code}" -X DELETE "$BASE/looks/$LOOK_ID" -H "$AUTH")
assert_status "DELETE /looks/:id" "$HTTP" "204"

HTTP=$(curl -s -o /dev/null -w "%{http_code}" -X DELETE "$BASE/account/me" -H "$AUTH")
assert_status "DELETE /account/me (account deleted)" "$HTTP" "204"

HTTP=$(curl -s -o /dev/null -w "%{http_code}" "$BASE/auth/me" -H "$AUTH")
assert_status "  → deleted user rejected (401)" "$HTTP" "401"

echo ""
echo -e "${GREEN}All tests complete.${NC}"
echo "  Base URL : $BASE"
echo "  Test user: $EMAIL"
echo ""
echo "Add your API keys to backend/.env to enable AI endpoint tests:"
echo "  GROQ_API_KEY=...   → groq.com (free)"
echo "  GOOGLE_API_KEY=... → aistudio.google.com (free)"
