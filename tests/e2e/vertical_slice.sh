#!/usr/bin/env bash
# Vertical slice: login → upload → scan → embed → generate → retrieve.
# Runs against the local dev stack (node-gateway on 127.0.0.1:3001).
set -euo pipefail

GW="${GW:-http://127.0.0.1:3001}"
EMAIL="${EMAIL:-demo@opengrow.dev}"
PASSWORD="${PASSWORD:-demo-password-change-me}"

need() { command -v "$1" >/dev/null || { echo "missing: $1"; exit 1; }; }
need curl
need jq

json() { echo "$1" | jq -r "$2"; }

echo "== 1) Login =="
TOKEN=$(curl -sf -X POST "$GW/auth/login" \
	-H "Content-Type: application/x-www-form-urlencoded" \
	--data-urlencode "username=$EMAIL" \
	--data-urlencode "password=$PASSWORD" | jq -r .access_token)
[ -n "$TOKEN" ] || { echo "login failed"; exit 1; }
echo "  got JWT"

echo
echo "== 2) Upload a text asset =="
TMP=$(mktemp)
cat > "$TMP" <<'EOF'
OpenGrow brand voice guide:
- Tone: direct, no jargon, technical.
- Audience: solo founders shipping SaaS.
- Do: focus on ROI-provable content and self-hosted freedom.
- Do not: use words like "leverage", "synergy", "cutting-edge".
EOF

UPLOAD=$(curl -sf -X POST "$GW/api/assets/upload" \
	-H "Authorization: Bearer $TOKEN" \
	-F "file=@$TMP;type=text/plain;filename=brand.txt")
ASSET_ID=$(json "$UPLOAD" .asset_id)
[ -n "$ASSET_ID" ] || { echo "upload failed: $UPLOAD"; exit 1; }
echo "  asset_id=$ASSET_ID"

echo
echo "== 3) Poll until INDEXED (max 60s) =="
for i in $(seq 1 30); do
	STATUS=$(curl -sf -H "Authorization: Bearer $TOKEN" "$GW/api/assets/$ASSET_ID" | jq -r .status)
	echo "  [$i] status=$STATUS"
	[ "$STATUS" = "INDEXED" ] && break
	[ "$STATUS" = "SCAN_FAILED" ] || [ "$STATUS" = "EMBED_FAILED" ] && { echo "  failed"; exit 1; }
	sleep 2
done
[ "$STATUS" = "INDEXED" ] || { echo "  timeout"; exit 1; }

echo
echo "== 4) Create generation =="
GEN=$(curl -sf -X POST "$GW/api/generations" \
	-H "Authorization: Bearer $TOKEN" \
	-H "Content-Type: application/json" \
	-d "{\"brief\":\"Write a 3-tweet thread introducing OpenGrow to solo founders.\",\"reference_asset_id\":\"$ASSET_ID\",\"model\":\"gpt-4o-mini\"}")
GEN_ID=$(json "$GEN" .id)
[ -n "$GEN_ID" ] || { echo "generation create failed: $GEN"; exit 1; }
echo "  generation_id=$GEN_ID"

echo
echo "== 5) Poll until COMPLETE (max 120s) =="
for i in $(seq 1 60); do
	STATUS=$(curl -sf -H "Authorization: Bearer $TOKEN" "$GW/api/generations/$GEN_ID" | jq -r .status)
	echo "  [$i] status=$STATUS"
	[ "$STATUS" = "COMPLETE" ] && break
	[ "$STATUS" = "FAILED" ] && { echo "  failed"; exit 1; }
	sleep 2
done
[ "$STATUS" = "COMPLETE" ] || { echo "  timeout"; exit 1; }

echo
echo "== 6) Retrieve result =="
curl -sf -H "Authorization: Bearer $TOKEN" "$GW/api/generations/$GEN_ID" | jq

echo
echo "PASS ✅"
