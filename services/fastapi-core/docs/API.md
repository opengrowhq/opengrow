# OpenGrow Core API — frontend reference

The full, always-current contract is the OpenAPI spec:

- Interactive docs: **`GET /docs`** (Swagger UI, non-prod)
- Raw schema: **`GET /openapi.json`**

This file covers the cross-cutting conventions a client needs; use `/docs` for
exact request/response shapes per endpoint.

## Base URL

| Mode | Base URL | Notes |
|---|---|---|
| Lite (dev) | `http://localhost:8000` | browser → FastAPI directly |
| Production | the node-gateway URL | browser → gateway → FastAPI (`NEXT_PUBLIC_API_BASE`) |

Paths are identical in both modes (e.g. `/content`, `/analytics/summary`).

## Auth

- `POST /auth/login` — OAuth2 password form (`username`, `password`, form-encoded)
  → `{ access_token, refresh_token, token_type: "bearer" }`.
- Send `Authorization: Bearer <access_token>` on every other call.
- `GET /auth/me` → `{ id, email, display_name, tenant_id, tenant_slug }`.
- `401` on missing/invalid/expired token.
- Self-service signup is not part of the open-source core — workspace
  creation is seed/script-only (`make seed`); registration endpoints
  return 404 here.

## Versioning

`GET /version` → `{ service, version, mode, env }`. Feature-detect against
`version` (semver).

## Pagination (list endpoints)

List endpoints return a **plain JSON array**. Opt into paging with query params;
the unpaginated total comes back in a header:

- `?limit=<1..200>` — max items (omit → all)
- `?offset=<n>` — rows to skip
- Response header **`X-Total-Count`** — total rows for the (filtered) query
  (exposed via CORS)

Covered: `GET /content`, `GET /brands`, `GET /analytics/events`.

## Errors

All errors are JSON with a **string** `detail`:

```json
{ "detail": "human-readable message" }
```

Validation errors (`422`) additionally include a structured `errors` array
(the raw pydantic error list). Common codes: `400` bad input, `401`
unauthenticated, `403` not permitted, `404` not found / not your tenant,
`409` illegal state transition, `422` validation, `502` upstream (e.g.
GitHub).

## Async jobs (poll pattern)

`POST /assets/upload` and `POST /generations` return `202 Accepted` with an id;
poll the corresponding `GET /assets/{id}` / `GET /generations/{id}` until the
status reaches a terminal state (`INDEXED`/`COMPLETE`/`FAILED`).

## Multi-tenancy

Every resource is scoped to the caller's tenant. Cross-tenant reads/mutations
return `404`. The tenant is derived from the token — clients never pass a tenant id.

## Endpoint groups

Core: `/auth`, `/assets`, `/generations`, `/content`, `/brands`, `/analytics`.
Added for the platform build-out (see `/docs` for shapes):

- **`/api-keys`** — create (returns the secret once)/list/revoke keys. Authenticate
  any endpoint headlessly with `X-API-Key: <key>` instead of a Bearer token.
- **`/usage`**, **`/usage/summary`** — per-tenant metering (units + cost by kind).
- **Publishing** — `GET /content/publish/channels` (channels + `implemented`
  flag), `POST /content/{id}/publish` `{channel, config}` for WordPress, Ghost,
  Webflow, Email, X, and LinkedIn (BYOK creds in `config`); GitHub keeps its own
  `POST /content/{id}/publish/github`. Config hosts are SSRF-guarded; a missing/
  bad config → `502`.
- **GitHub publishing credentials** — `GET /content/publish/github/config`
  reports `{configured, api_url, source, has_tenant_credential, token_last4}`.
  `source` is `"tenant"` when a tenant PAT is stored, `"env"` when the instance
  `GITHUB_TOKEN` fallback is used, or `null` when publishing is not configured.
  `POST /content/publish/github/credentials` with `{token, display_name?}` stores
  or replaces the tenant PAT and returns only redacted metadata. The token is
  validated against GitHub (`GET /user`) before storing — an invalid token →
  `400` and nothing is persisted. `DELETE
  /content/publish/github/credentials` removes the tenant PAT; publishing then
  falls back to `GITHUB_TOKEN` if present. Tokens are never returned by the API.
- **`/orchestrator/runs`** — `POST` starts a content run (returns `run_id`),
  `GET /orchestrator/runs/{id}` polls status/result. With an `article` brief,
  the run drives the full pipeline: keyword research (skipped if you already
  supply `primary_keyword`) → outline → optional human-approval pause
  (`POST /orchestrator/runs/{id}/outline/approve`) → draft → a quality gate
  that regenerates a low-scoring draft with feedback (up to a fixed retry
  budget) before it's ever promoted → promote → guarded publish.
- **`/playbooks`** — versioned, tenant-customizable system prompts for
  outline/draft/generic-copy generation. `POST` saves a new version (never
  edits in place), `POST /playbooks/{id}/activate` makes it the active one;
  falls back to a global default, then a built-in default, if a tenant never
  customizes it.
- **Content calendar** — set `due_at` + `scheduled_publish: {channel, config}`
  on a `ContentPiece` (`POST`/`PATCH /content`) and an hourly sweep publishes
  it automatically once it's `APPROVED` and due, through the same publisher
  adapters as a manual `POST /content/{id}/publish`.
- **`/analytics/recommendations`** — `GET` lists suggestions computed daily
  from real trend data: `REFRESH` for decaying content, `DOUBLE_DOWN` for
  growing content, `NEW_TOPIC` for a tag that shows up on only one published
  piece (a topic touched once, never built into a cluster — a weaker,
  co-occurrence-only signal, always scored below the two trend-backed kinds).
  `POST .../dismiss` or `POST .../start-run` (turns a suggestion straight
  into a new orchestrator run; `NEW_TOPIC` suggestions have no
  `content_piece_id`, since they're tenant-wide gaps, not per-piece).
- **`/analytics/stripe/credentials`**, **`/analytics/stripe/config`** — BYOK:
  connect your OWN Stripe account (not OpenGrow's billing) so your customers'
  `charge.succeeded` events attribute revenue back to content automatically,
  via `POST /analytics/stripe/webhook/{tenant_id}` (signature-verified against
  your stored webhook secret).
- **`/mcp`** — MCP JSON-RPC endpoint for AI agents (initialize / tools/list /
  tools/call); auth via `X-API-Key`. Tools mirror the REST surface —
  content/brands (`list_content`, `create_content`, `transition_content`,
  `list_brands`), generations (`create_generation`, `get_generation`,
  `list_generations`), orchestrator runs (`create_orchestrator_run`,
  `get_orchestrator_run`, `list_orchestrator_runs`), the article pipeline
  (`create_article_run` — flattens `ArticleBrief`'s fields as top-level tool
  arguments; `approve_article_outline` — takes `run_id` + an outline section
  list once a run reports `AWAITING_OUTLINE_APPROVAL`), analytics connectors
  (`list_analytics_connectors`, `sync_analytics_connector`), recommendations
  (`list_recommendations`, `dismiss_recommendation`,
  `start_run_from_recommendation`), publications (`list_publications`), and
  attribution (`get_attribution_summary`). Write tools call the same
  REST-router functions the HTTP endpoints use, so authz/business logic
  isn't re-derived.

Rate limiting (per key/token/IP) is available but off by default; when a
deployment enables it, expect `429` + `Retry-After`.
