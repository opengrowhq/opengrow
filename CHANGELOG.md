# Changelog

All notable changes to OpenGrow are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project aims to
follow [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

**Generate**
- Versioned playbooks (`/playbooks`): tenant-customizable system prompts for
  outline/draft/generic-copy generation, falling back to a global then
  built-in default. New versions are saved as new rows, never edited in
  place.

**Orchestrate**
- Keyword research step: a bare topic gets a real primary/secondary keyword
  set via no-API-key scraping (Google Autocomplete + Bing SERP/PAA) —
  skipped automatically when a keyword is already supplied.
- Quality gate: a draft that scores too low on keyword/heading coverage,
  length, and readability is regenerated with feedback before it's ever
  promoted, up to a fixed retry budget, rather than silently publishing a
  weak draft.

**Publish**
- Content calendar scheduled auto-publish: set `due_at` +
  `scheduled_publish: {channel, config}` on a content piece and an hourly
  sweep publishes it automatically once it's approved and due, through the
  same channel adapters as a manual publish.

**Attribute**
- Real backend attribution recommendations (`/analytics/recommendations`):
  a daily sweep flags decaying published content to refresh and growing
  content to double down on, computed from real trend data — replacing the
  prior rule-based, client-side-only advisory panel.
  `POST .../start-run` turns a recommendation directly into a new
  orchestrator run, closing the content → attribution → next-content loop
  for real.
- `NEW_TOPIC` recommendations: the daily sweep also flags topic gaps — a
  tag that shows up on only one published piece — as a third suggestion
  kind, scored below the trend-backed REFRESH/DOUBLE_DOWN signals since it's
  co-occurrence-only, not attribution data.
- Recommendations are now visible in the Analytics dashboard (previously
  API/MCP-only): a panel lists pending suggestions with their rationale and
  Dismiss / Start-run actions, alongside the existing rule-based "Next
  moves" nudges.
- Tenant-owned Stripe revenue sync (`/analytics/stripe/*`): connect your own
  Stripe account (BYOK, separate from OpenGrow's own platform billing) so
  `charge.succeeded` events attribute revenue back to content automatically.

**Platform**
- MCP coverage for analytics connectors and recommendations
  (`list_analytics_connectors`, `sync_analytics_connector`,
  `list_recommendations`, `dismiss_recommendation`,
  `start_run_from_recommendation`) and the article pipeline
  (`create_article_run`, `approve_article_outline`) — an agent can now
  drive the full research → outline → approve → draft → promote → publish
  cycle, and the attribution → recommendation → next-run loop, without
  leaving the MCP tool surface. 19 tools total.

## [0.1.0] — Pre-Alpha

First public pre-alpha. The full growth loop — **context → content → publish →
attribution** — runs locally, in both Lite (personal) and Production
(multi-tenant) shapes from a single codebase.

### Added

**Core & tenancy**
- Multi-tenant FastAPI backend with JWT auth and row-level `tenant_id` isolation
  (Production also enforces OpenFGA ReBAC).
- Next.js tenant app under `/app/{slug}/…` (dashboard, Brand DNA, Library, editor,
  calendar, onboarding). Open-source root redirects to `/login`.

**Generate**
- Brand/context asset upload with async processing (MinIO + Celery + embeddings;
  Qdrant in Production).
- AI generation from a brief with uploaded assets as context — bring your own
  OpenAI / Anthropic / Google, or run free & local with Ollama.
- Content lifecycle: draft → review → approve → Markdown export, with status and
  next-action planning.

**Publish**
- GitHub PR publishing (the wedge): approve a piece and OpenGrow opens or reuses a
  reviewable pull request on your repo, with publication history and
  merge-to-`PUBLISHED` refresh.
- Additional BYOK channels via `POST /content/{id}/publish`: WordPress, Ghost,
  Webflow, Email (SMTP), X, and LinkedIn.

**Attribute**
- First-party tracking pixel + conversion capture (VISIT / SIGNUP / LEAD /
  CUSTOMER / REVENUE), deduped by `external_id`.
- Manual + GA4 / GSC import and connector sync; per-content / channel / source
  breakdowns and time-windowed trend deltas.
- Attribution summary tying content → pipeline → revenue.

**Platform**
- First-class headless REST API: API keys (`X-API-Key`), `limit/offset` +
  `X-Total-Count` pagination, `GET /version`; reference in `docs/API.md`.
- MCP server (`/mcp`) so AI agents (Claude Code, Cursor) can drive OpenGrow.
- Single-call content cycle (`/orchestrator/runs`), per-tenant usage metering
  (`/usage`), and an optional Redis rate limiter (off by default).

**Deployment**
- Lite (5 services, ~5-minute `make lite-up`) and Production (15 services,
  Infisical secrets, Caddy auto-TLS, ClamAV, LiteLLM proxy, Qdrant) from the same
  `services/fastapi-core/app/` code, switched by `DEPLOYMENT_MODE`.

[Unreleased]: https://github.com/opengrowhq/opengrow/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/opengrowhq/opengrow/releases/tag/v0.1.0
