# OpenGrow Frontend

Next.js (App Router, TypeScript, Tailwind) frontend for OpenGrow. Talks to the
`fastapi-core` API — directly in lite mode, via the `node-gateway` BFF in
production.

## Run (dockerized — recommended)

The frontend is a service in the lite stack. From the repo root:

```bash
make lite-up && make lite-migrate && make lite-seed
```

This starts the backend **and** the frontend (hot-reload dev target) at
http://localhost:3000. Sign in with the seeded demo user:

- Email: `demo@opengrow.dev`
- Password: `123456`

Ports/API base are configurable via `HOST_FRONTEND_PORT` /
`NEXT_PUBLIC_API_BASE` (see `.env.lite.example`).

## Run outside Docker (optional, for frontend-only iteration)

```bash
cd services/frontend
cp .env.example .env.local        # defaults to http://localhost:8000 (lite)
npm install
npm run dev                       # http://localhost:3000
```

## Docker image targets

- `dev` — hot-reload server (used by `docker-compose.lite.yml`).
- `runner` — minimal non-root production image from Next standalone output
  (`output: "standalone"`), for the production compose / hosting.

## What the scaffold does

- **`/`** — redirects to `/login` (the open-source app has no marketing or
  pricing pages; those are hosted-only surfaces).
- **`/login`** — form login (form-encoded to `POST /auth/login`).
- **`/app/[slug]`** — tenant pages/slugs dashboard.
- **`/app/[slug]/brand`** — Brand DNA management.
- **`/app/[slug]/content`** — content library.
- **`/app/[slug]/content/[id]`** — content editor, lifecycle, export, and publish actions.
- **`/app/[slug]/calendar`** — content calendar grouped by due date and next action.
- **`/app/[slug]/onboarding`** — brand onboarding flow.

After login, the user is redirected to `/app/{tenant_slug}`. Protected app pages
must stay under `/app/[slug]/...`; legacy top-level protected paths redirect to
`/login`.

## GitHub PR publishing UI

The content editor includes the first publish channel:

1. Transition content to `APPROVED`.
2. Ensure the backend has `GITHUB_TOKEN` configured.
3. Enter `owner/repo`; optional defaults are shown for path, base branch, publish
   branch, commit message, PR title, and PR body.
4. Submit to `POST /content/{id}/publish/github`.
5. Publication history appears in the editor with `PR_OPENED`, `PUBLISHED`, or
   `FAILED`.
6. After merging the PR, click **Refresh status** to call
   `POST /content/{id}/publications/{publication_id}/refresh`; merged PRs mark
   the content piece as `PUBLISHED`.

## Analytics surface

`/app/[slug]` reads `GET /analytics/summary`, `GET /analytics/content`,
`GET /analytics/channels`, and `GET /analytics/sources` to show attributed
revenue, top content, normalized channels, and source breakdowns. The dashboard
also includes a compact import panel that posts aggregate manual, GA4, or GSC
rows to `POST /analytics/import`; the backend upserts repeated rows by dedupe key
so connector refreshes do not double-count. A connector panel stores GA4/GSC
setup records through `GET/POST /analytics/connectors` and can request
`GET /analytics/connectors/google/auth-url?provider=ga4|gsc` when Google OAuth
env vars are configured, then submit an OAuth code to
`POST /analytics/connectors/{id}/google/callback`. Connected connectors expose a
manual Sync action backed by `POST /analytics/connectors/{id}/sync`. The
lower-level `POST /analytics/events` endpoint remains available for direct event
ingestion. Sync fetches GSC page rows and GA4 landing-page rows into deduped
attribution events, and connected connector syncs are enqueued daily by Celery
beat. First-party tracking uses `GET /analytics/pixel.gif?tenant={slug}` for
visits, `POST /analytics/track` for conversions, and
`GET /analytics/tracking/status` for install state. Helper functions in
`features/analytics/tracking-snippet.mjs` build embeddable pixel and
signup/lead/customer/revenue conversion snippets, and `/app/[slug]` exposes them
with install status in the Tracking panel. The dashboard applies 7/30/90/all
time-window controls to attribution reads. `features/analytics/funnel.mjs`
derives executive conversion metrics from `GET /analytics/summary`, while
`features/analytics/recommendations.mjs` turns the same attribution signals into
dashboard next moves. `GET /analytics/trends?days=30` powers previous-period
trend deltas and paired current/previous bars on executive metrics.
`GET /analytics/channel-trends?days=30`,
`GET /analytics/source-trends?days=30`, and
`GET /analytics/content-trends?days=30` power compact grouped trend bars.

## Content planning

Content pieces expose `next_action` and `due_at` metadata. The editor can update
those fields even after copy approval, and `/app/[slug]/calendar` groups content
into Overdue, Today, Tomorrow, and Later columns.

> Note: in lite mode without an LLM key configured in the backend `.env`, the
> embed and generate steps end in `EMBED_FAILED` / `FAILED` — expected. Set
> `OPENAI_API_KEY` (or another provider key, or run Ollama) in the repo-root
> `.env` and `make lite-down && make lite-up` to see them complete.

## Conventions

- API client: `src/lib/http.ts` (typed fetch helpers) plus a per-feature
  `api.ts` in each `src/features/<area>/` (single source of endpoint calls).
- Auth token: `src/lib/auth.ts` (localStorage for now; moves to an httpOnly
  cookie via the BFF in a later phase).
- Tenant app links: `src/lib/app-routes.mjs`; do not hardcode top-level
  protected routes such as `/content`, `/brand`, or `/onboarding`.
- Tests: `npm test` runs focused Node tests. New UI functionality must include
  focused tests in the same change; add the closest useful lower-level coverage
  until the full browser harness exists.
- Dependency freshness / zero-CVE policy applies (see root `AGENTS.md`); a
  `postcss` override keeps the transitive dep on a patched line.
