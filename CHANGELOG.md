# Changelog

All notable changes to OpenGrow are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project aims to
follow [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- feat(core): 35 content-creation methodology playbooks (SEO, schema, E-E-A-T,
  formatting, readability, repurposing, and more) ship as seeded global
  defaults — one active system playbook per generation kind
  (ARTICLE_OUTLINE / ARTICLE_DRAFT / GENERIC_COPY, `tenant_id NULL`) via
  migration `029_seed_system_playbooks`; every generation uses them out of the
  box and a tenant playbook still overrides the global default for its kind.

- feat: httpOnly cookie sessions via node-gateway — `og_at`/`og_rt` cookies
  on login/refresh/set-password/invite-accept, tokens stripped from response
  bodies, `x-og-auth` mode header, gateway-local `POST /auth/logout` +
  `POST /auth/session`; lite mode (Bearer tokens) unchanged; core CORS
  `allow_credentials=True`.
- feat(frontend): Google OAuth login button (shown only when the backend
  mounts the hosted OAuth routes) with a token-fragment handoff via
  `POST /auth/session`.
- feat(frontend): token refresh wiring — proactive refresh near access-token
  expiry plus a 401 single-flight retry.
- feat: frontend service in the production compose stack (16 services) with
  real `Caddyfile.prod` routing and `NEXT_PUBLIC_*` build args.
- feat: gateway proxies `/billing` for hosted overlay deployments, including
  public provider webhook paths (`/billing/webhook`,
  `/billing/webhook/{provider}`).

## [0.3.0] — Billing removed from core

The billing features that shipped in 0.2.0 (Stripe Checkout/Billing
Portal, prepaid credit balance with hold/settle/refund on generations, and
seat-based Team pricing) have been removed from the open-source core. The
core is billing-unaware again — generations and orchestrator runs queue
unconditionally and are metered via the usage ledger only.

### Removed

- `/billing/*` endpoints (checkout, portal, top-up, status, webhook) and the
  frontend Billing settings card.
- Credit gating: `debit_credits`/`InsufficientCredits` on
  `POST /generations`, and the hold/settle/refund credit accounting in
  `run_generation` and the orchestrator pipelines.
- Billing columns on `tenants` (`stripe_customer_id`, `billing_plan`,
  `credit_balance_cents`) and the `subscriptions` /
  `stripe_webhook_events` tables.
- `STRIPE_*` and `TEAM_INCLUDED_SEATS` settings/env vars (tenant-owned
  Stripe *revenue analytics* under `/analytics/stripe/*` is unchanged — it
  is BYOK per-tenant attribution, not platform billing).
- Self-service signup `POST /auth/signup` — a Production-mode concern that
  shipped alongside in-core billing; removed with it. Workspace creation in
  the core is seed/script-only again (`make seed`).

### Migrations

- Alembic revisions `022_billing_subscription`, `023_credit_balance`, and
  `025_seat_billing` are gone; the chain is now
  ...→ `021_slack_publication_channel` → `024_invites` → `026_playbooks` →
  `027_content_recommendations` → `028_tenant_stripe_revenue`.
- Existing dev databases that already applied the removed revisions should
  be reset (`make lite-down && make lite-up`, or drop/recreate the DB), or
  stamped to the new head with `alembic stamp 028_tenant_stripe_revenue` after reconciling
  manually.

## [0.2.0] — Orchestrator, billing, and the attribution feedback loop

Everything since `v0.1.0`: a self-driving content orchestrator (research →
outline → approve → draft → quality gate → publish → recommend → repeat),
usage-based billing (removed in 0.3.0), and MCP coverage across the whole
surface — 19 tools, up from the base `/mcp` server.

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
- Slack channel adapter (BYOK Incoming Webhook), joining the existing
  WordPress/Ghost/Webflow/Email/X/LinkedIn set.
- Content calendar scheduled auto-publish: set `due_at` +
  `scheduled_publish: {channel, config}` on a content piece and an hourly
  sweep publishes it automatically once it's approved and due, through the
  same channel adapters as a manual publish.

**Attribute**
- CSV bulk import for revenue events, alongside the existing manual/GA4/GSC
  import paths.
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
  Stripe account (BYOK — your own keys, used only to read `charge.succeeded`
  events) so revenue attributes back to content automatically.

**Team**
- Team-member invites (backend + frontend): admin-only invite by email,
  token-based no-auth accept flow, tenant member roster and removal.

**Billing** (Production mode — all of the below removed in 0.3.0)
- Self-service tenant signup (`POST /auth/signup`) — no more requiring
  `make seed` to create the first workspace.
- Stripe-hosted Checkout + Billing Portal for Pro/Team plans, with
  signature-verified, idempotent subscription webhooks.
- Prepaid credit balance with a hard stop on exhausted credit (never a
  silent overage charge), billed by real per-model LLM cost — held before
  the call, settled after, refunded on failure.
- Purchased credit top-ups (fixed tiers) for tenants who need
  more than their plan's included allowance before renewal.
- Seat-based Team pricing: a base number of included seats, with additional
  seats billed automatically as members are invited or removed.
- Past-due/dunning warning on the Billing settings card with a direct link
  into the Stripe Portal to update a failed payment method.

**Platform**
- MCP coverage across content, brands, generations, the orchestrator
  (including the full article pipeline — `create_article_run`,
  `approve_article_outline`), analytics connectors, and recommendations
  (`list_analytics_connectors`, `sync_analytics_connector`,
  `list_recommendations`, `dismiss_recommendation`,
  `start_run_from_recommendation`) — an agent can now drive the full
  research → outline → approve → draft → promote → publish cycle, and the
  attribution → recommendation → next-run loop, without leaving the MCP
  tool surface. 19 tools total, up from the base server.

### Fixed
- Billing checkout no longer misreports a configured-but-unpriced plan as
  "unknown plan" (400) instead of "billing not configured" (503).
- A latent `datetime` JSON-serialization gap in the MCP JSON-RPC handler
  that would have crashed any tool returning a model with a real timestamp
  field.
- A sweep-dedup bug that would have collapsed every distinct `NEW_TOPIC`
  gap suggestion into a single pending row, since they share no
  `content_piece_id` to dedupe on.
- Three dependency security advisories (`nanoid`, `js-yaml`,
  `brace-expansion`) pinned to patched versions.

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
- Lite (8 services, ~5-minute `make lite-up`) and Production (15 services,
  Infisical secrets, Caddy auto-TLS, ClamAV, LiteLLM proxy, Qdrant) from the same
  `services/fastapi-core/app/` code, switched by `DEPLOYMENT_MODE`.

[Unreleased]: https://github.com/opengrowhq/opengrow/compare/v0.3.0...HEAD
[0.3.0]: https://github.com/opengrowhq/opengrow/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/opengrowhq/opengrow/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/opengrowhq/opengrow/releases/tag/v0.1.0
