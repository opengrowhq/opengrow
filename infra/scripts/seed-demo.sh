#!/usr/bin/env bash
# Seed a RUNNING lite-mode instance with the examples/ fixtures — one command
# to get a fresh instance demo-ready (brand context, content pieces, and
# attribution data). Idempotent-ish: safe to re-run (content pieces will
# duplicate; analytics import dedupes by its own keys).
#
#   make lite-up && make lite-migrate && make lite-seed   # tenant + demo user
#   make seed-demo                                        # this script
#
# Override the target with GW=... (default http://127.0.0.1:8000).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
GW="${GW:-http://127.0.0.1:8000}"
EMAIL="${DEMO_EMAIL:-demo@opengrow.dev}"
PASSWORD="${DEMO_PASSWORD:-123456}"

echo "== Seeding demo fixtures → $GW =="

command -v python3 >/dev/null || { echo "python3 is required"; exit 1; }

# 1. Log in as the demo user (created by 'make lite-seed').
TOKEN=$(curl -sf -X POST "$GW/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  --data-urlencode "username=$EMAIL" --data-urlencode "password=$PASSWORD" \
  | python3 -c 'import sys,json;print(json.load(sys.stdin).get("access_token",""))') || true
if [ -z "${TOKEN:-}" ]; then
  echo "!! login failed. Is the stack up and seeded? Run: make lite-up && make lite-migrate && make lite-seed"
  exit 1
fi
AUTH="Authorization: Bearer $TOKEN"

# 2. Brand context asset (upload → scan → embed → index).
echo "-> uploading brand context (brand-voice-founder-saas.txt)"
curl -sf -X POST "$GW/assets/upload" -H "$AUTH" \
  -F "file=@$ROOT/examples/brand-voice-founder-saas.txt;type=text/plain" >/dev/null \
  && echo "   ok (poll GET /assets/{id} for INDEXED)" || echo "   !! upload failed"

# 3. Content pieces from the example briefs.
echo "-> creating content pieces from content-briefs.json"
python3 - "$GW" "$TOKEN" "$ROOT/examples/content-briefs.json" <<'PY'
import sys, json, urllib.request, urllib.error
gw, token, path = sys.argv[1], sys.argv[2], sys.argv[3]
briefs = json.load(open(path))
made = 0
for b in briefs:
    payload = json.dumps({
        "title": b["topic"],
        "body": b.get("description", ""),
        "format": "markdown",
    }).encode()
    req = urllib.request.Request(f"{gw}/content", data=payload, method="POST",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"})
    try:
        urllib.request.urlopen(req); made += 1
    except urllib.error.HTTPError as e:
        print(f"   skip '{b['topic'][:40]}…': {e.code}")
print(f"   created {made}/{len(briefs)} content pieces")
PY

# 4. Attribution data (aggregate import, provider=manual).
for f in analytics-events revenue-events; do
  echo "-> importing $f.csv"
  python3 - "$GW" "$TOKEN" "$ROOT/examples/$f.csv" <<'PY'
import sys, csv, json, urllib.request, urllib.error
gw, token, path = sys.argv[1], sys.argv[2], sys.argv[3]
def i(v):
    try: return int(v)
    except (TypeError, ValueError): return 0
rows = []
for r in csv.DictReader(open(path)):
    rows.append({
        "source_url": (r.get("source_url") or None),
        "channel": (r.get("channel") or None),
        "external_id": (r.get("external_id") or None),
        "visits": i(r.get("visits")), "signups": i(r.get("signups")),
        "leads": i(r.get("leads")), "customers": i(r.get("customers")),
        "revenue_cents": i(r.get("revenue_cents")),
        "currency": (r.get("currency") or "USD"),
        "occurred_at": (r.get("occurred_at") or None),
    })
payload = json.dumps({"provider": "manual", "rows": rows}).encode()
req = urllib.request.Request(f"{gw}/analytics/import", data=payload, method="POST",
    headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"})
try:
    out = json.load(urllib.request.urlopen(req))
    print(f"   imported_events={out.get('imported_events')} rows={out.get('imported_rows')}")
except urllib.error.HTTPError as e:
    print(f"   !! import failed: {e.code} {e.read().decode()[:200]}")
PY
done

FRONT="${FRONTEND_URL:-${GW%:*}:3000}"
echo "== Demo seed complete =="
echo "   Frontend: $FRONT/app/demo    API docs: $GW/docs    Login: $EMAIL / $PASSWORD"
