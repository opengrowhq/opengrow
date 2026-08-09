# First demo walkthrough

An end-to-end run of the OpenGrow loop on the **lite** stack:
**brand context → generate → GitHub PR publish → revenue attribution**.

It uses the fixtures shipped in [`examples/`](../examples):

| File | Used for |
|---|---|
| `examples/brand-voice-founder-saas.txt` | Brand context asset (upload → embed → grounding) |
| `examples/content-briefs.json` | Article/content briefs to generate from |
| `examples/sample-content-repo/` | A target repo layout for GitHub PR publishing |
| `examples/analytics-events.csv` | Import outcome events (VISIT/SIGNUP/…) |
| `examples/revenue-events.csv` | Import revenue events for attribution |

> Ports below are the lite defaults (`127.0.0.1:8000` API, `127.0.0.1:3000`
> frontend). If you remapped them (see `.env`), substitute your own.

## 0. Bring the stack up

```bash
cp .env.lite.example .env
$EDITOR .env            # set OPENAI_API_KEY, or use local Ollama (free)
make lite-up
make lite-migrate
make lite-seed          # demo tenant: demo@opengrow.dev / 123456
```

For the free, fully-local path, pull the Ollama models first and leave
`DEFAULT_LLM_MODEL=ollama/llama3.1`:

```bash
docker compose -f docker-compose.lite.yml exec ollama ollama pull llama3.1
docker compose -f docker-compose.lite.yml exec ollama ollama pull nomic-embed-text
```

Get a token for the API calls below:

```bash
GW=http://127.0.0.1:8000
TOKEN=$(curl -sf -X POST $GW/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  --data-urlencode "username=demo@opengrow.dev" \
  --data-urlencode "password=123456" | jq -r .access_token)
```

## 1. Upload brand context (upload → scan → embed → index)

```bash
UPLOAD=$(curl -sf -X POST $GW/assets/upload \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@examples/brand-voice-founder-saas.txt;type=text/plain")
ASSET_ID=$(echo "$UPLOAD" | jq -r .asset_id)

# Wait for INDEXED — only then is it usable as generation grounding.
while [ "$(curl -sf -H "Authorization: Bearer $TOKEN" $GW/assets/$ASSET_ID | jq -r .status)" != "INDEXED" ]; do
  sleep 2
done
```

The asset moves `UPLOADED → SCANNING → SCANNED → EMBEDDING → INDEXED`
(see [upload-pipeline.md](./upload-pipeline.md)). In lite mode the ClamAV scan
is skipped and embeddings are ranked from Postgres.

## 2. Generate an article (outline → approve → draft)

Drive it from the UI at `http://127.0.0.1:3000/app/demo/articles`, or via the
orchestrator in one call using a brief from `examples/content-briefs.json`:

```bash
RUN=$(curl -sf -X POST $GW/orchestrator/runs \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{
    "brief": "How technical founders can turn a docs repo into a growth engine",
    "article": {
      "topic": "Docs-repo-driven content growth for founders",
      "primary_keyword": "founder content workflow",
      "audience": "technical founders",
      "goal": "educate"
    },
    "pause_for_outline_approval": true
  }')
RUN_ID=$(echo "$RUN" | jq -r .run_id)
```

With `pause_for_outline_approval: true` the run stops at
`AWAITING_OUTLINE_APPROVAL`. Review and approve the outline (UI, or
`POST /orchestrator/runs/$RUN_ID/approve-outline`), and the run continues to a
full Markdown draft saved as a content piece.

## 3. Publish as a GitHub pull request

Set `GITHUB_TOKEN` in `.env` (a fine-grained or classic PAT with **Contents**
and **Pull requests** write on the target repo) and restart. Then approve the
piece and publish. You can point at your own repo, or mirror the layout in
`examples/sample-content-repo/`:

```bash
curl -sf -X POST $GW/content/$CONTENT_ID/publish \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{
    "channel": "github",
    "config": { "owner": "your-org", "repo": "your-content-repo",
                "path": "content/posts/founder-content-workflow.md",
                "base_branch": "main" }
  }'
```

OpenGrow writes the Markdown to an `opengrow/{content_id}` branch and opens (or
reuses) a PR. After you merge it, hit **Refresh status** on the publication (or
`POST /publications/{id}/refresh`) and the publication + content piece flip to
`PUBLISHED`. Full setup: [publishing-github.md](./publishing-github.md).

## 4. Attribute traffic and revenue

Import the sample outcome and revenue events, then read the attribution rollups:

```bash
curl -sf -X POST $GW/analytics/import \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  --data-binary @examples/analytics-events.csv     # or the documented JSON import shape

curl -sf -H "Authorization: Bearer $TOKEN" "$GW/analytics/summary"
curl -sf -H "Authorization: Bearer $TOKEN" "$GW/analytics/content?days=30"
curl -sf -H "Authorization: Bearer $TOKEN" "$GW/analytics/trends?days=30"
```

Or open `http://127.0.0.1:3000/app/demo/analytics` for the dashboard: KPI
summary, revenue funnel, per-content / channel / source breakdowns, and
time-windowed trend deltas. That closes the loop —
**content → traffic → conversion → revenue → better next content.**

See the [REST API reference](../services/fastapi-core/docs/API.md) for exact
request/response shapes.
