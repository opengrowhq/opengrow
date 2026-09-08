# Frontend Onboarding — OpenGrow

Welcome. You own the **frontend** (`services/frontend`); it's a client of a
stable, documented HTTP API. This doc gets you running and productive fast.

## 1. Run the backend locally (5 min)

Requires Docker Desktop / Docker Engine + Compose v2.

```bash
cp .env.lite.example .env      # optional: add OPENAI_API_KEY for real generation
make lite-up                   # starts the 8-service backend stack
make lite-migrate && make lite-seed
```

| URL | What |
|---|---|
| http://127.0.0.1:8000/docs | Live API (Swagger) — your source of truth |
| http://127.0.0.1:8000/openapi.json | Raw OpenAPI schema (generate a client if you like) |
| http://127.0.0.1:3000 | The current frontend |
| http://127.0.0.1:8025 | Mailpit (outgoing email inspector) |

**Demo login:** `demo@opengrow.dev` / `123456`

Full API conventions live in **`services/fastapi-core/docs/API.md`** — read it.

## 2. Run the frontend

```bash
cd services/frontend
npm install
npm run dev        # http://localhost:3000
npm test           # node --test *.mjs (logic tests)
npm run lint
```

`NEXT_PUBLIC_API_BASE` (default: **empty** = same-origin relative calls) points
the browser at the API. The empty default is required for cookie mode (the
gateway must be same-origin so the httpOnly cookies attach); Caddy routes
`/auth/*` and `/api/*` to the gateway. The lite compose sets it explicitly to
`http://localhost:8000` so the browser reaches fastapi-core directly.

## 3. Codebase map

```
services/frontend/src/
  app/                 # Next.js App Router pages
    login/             # /login  (reads ?next= for post-auth redirect)
    app/[slug]/        # authenticated, tenant-scoped app (dashboard, brand, content, calendar, onboarding)
  features/<domain>/   # auth, brand, content, analytics, slugs, studio
    api.ts             # typed fetch calls (use lib/http)
    hooks.ts           # TanStack Query hooks
    components/        # UI
  lib/
    http.ts            # apiGet / apiSend / API_BASE / ApiError — sends credentials: "include" on every call
    auth.ts            # both transports: lite keeps Bearer tokens in localStorage; cookie mode is flagged by the x-og-auth header
    app-routes.mjs     # appPath()/appRootPath()/resolvePostAuthPath()
    use-mounted.ts     # hydration-safe mount gate (see gotcha #1)
```

Stack: **Next.js 16 (App Router)**, React, TypeScript, Tailwind, **TanStack Query**.

## 4. API essentials

- **Auth:** two transports, both live (see `src/lib/auth.ts` + `src/lib/http.ts`):
  - **Lite** — `POST /auth/login` (form-encoded `username`/`password`) →
    `{ access_token, refresh_token }`, kept in localStorage and sent as
    `Authorization: Bearer <token>` on every other call.
  - **Gateway deployments (cookie mode)** — login/refresh/set-password/invite-accept
    responses come back with tokens stripped from the body and set as httpOnly
    `og_at`/`og_rt` cookies instead; the response carries an `x-og-auth: cookie`
    header the client reads to flip modes. Every fetch sends
    `credentials: "include"`; JavaScript never sees the tokens. The gateway
    serves `POST /auth/logout` (clears the cookies) and `POST /auth/session`
    (one-shot handoff for OAuth-callback URL fragments; requires
    `X-Requested-With: XMLHttpRequest`).
  - `GET /auth/me` → `{ id, email, tenant_id, tenant_slug }`.
- **Tenancy:** everything is scoped to the token's tenant. Never pass a tenant id;
  cross-tenant access → `404`.
- **Pagination (optional):** `?limit=&offset=` on list endpoints; total in the
  `X-Total-Count` response header. Omit → full list.
- **Errors:** always `{ "detail": "<string>" }` (422 also adds `errors[]`). `lib/http`
  throws `ApiError(status, detail)`.
- **Async jobs:** `POST /assets/upload` and `POST /generations` return `202` + an id;
  poll `GET /assets/{id}` / `GET /generations/{id}` until a terminal status.
- **Routes:** authenticated app pages are canonical under `/app/{tenant_slug}/...`.

Endpoint groups: `/auth`, `/content`, `/brands`, `/generations`, `/assets`,
`/analytics`, plus `/api-keys`, `/usage`, `/orchestrator`, `/mcp`. See `/docs`.

## 5. Gotchas (learn from our scars)

1. **Hydration.** Auth-gated pages are `"use client"` but still SSR'd; the token
   only exists client-side, so react-query state differs between server and first
   client render. Use `useMounted()` (`lib/use-mounted.ts`) + `first-paint.mjs` to
   keep the first paint deterministic. Don't branch UI on client-only state during render.
2. **This is not the Next.js you know.** Read `services/frontend/AGENTS.md` — Next 16
   has breaking changes; check `node_modules/next/dist/docs/` before reaching for
   old patterns. `useSearchParams` needs a `<Suspense>` boundary.
3. **Tests required.** Every changed UI behavior ships with a focused test
   (`*.test.mjs`, `node --test`). Auth redirects, list rendering, form logic.
4. **Generation needs a model.** Real content generation needs an LLM: set
   `OPENAI_API_KEY` in `.env`, or `docker compose -f docker-compose.lite.yml exec
   ollama ollama pull llama3.1` for free local. Everything else works without it.

## 6. What's out of scope for you

Marketing homepage, pricing, and billing UI are **not part of this repo** —
you don't need them. The open-source app boots straight to `/login`.

Questions → ping the team. Have fun. 🚀
