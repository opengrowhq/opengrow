# Frontend v0.1.0 — Acceptance Checklist

**Definition of done:** a new user can go from login to a published GitHub PR
entirely in the UI, against the real API, with loading/empty/error states handled
and no console/hydration errors. This is the wedge — it must feel solid.

Read `FRONTEND-ONBOARDING.md` first. Full API contract: `/docs` + `services/fastapi-core/docs/API.md`.

## The happy path (each step must work end-to-end)

| # | Flow | API calls | Acceptance |
|---|---|---|---|
| 1 | **Login** | `POST /auth/login` (form) → token; `GET /auth/me` | Wrong creds → inline error. Success → redirect to `/app/{tenant_slug}`. Token persisted; refresh keeps you in. |
| 2 | **Brand DNA / onboarding** | `POST /brands {name, source_url?}` → 202; poll `GET /brands/{id}` until `READY`/`FAILED`; `PATCH /brands/{id}` | Live stepper while `PENDING→SCRAPING→EXTRACTING→READY`. On `FAILED`, fall back to manual entry. Profile editable. |
| 3 | **Generate** | `POST /generations {brief}` → 202; poll `GET /generations/{id}` until `COMPLETE`/`FAILED` | Polling UI (not a frozen screen). `COMPLETE` → show result + "save as content". `FAILED` → readable error. |
| 4 | **Content library** | `GET /content` (`?limit=&offset=`, `X-Total-Count`); `POST /content`; `POST /content/from-generation` | List renders; empty state when none; create works; promote generation → content. Use pagination for long lists. |
| 5 | **Editor + lifecycle** | `GET/PATCH /content/{id}`; `POST /content/{id}/transition {status}` | Edit title/body; transitions follow the state machine (DRAFT→IN_REVIEW→APPROVED→PUBLISHED); illegal transition (409) surfaced, not crashed. |
| 6 | **Publish (the wedge)** | `GET /content/publish/github/config`; `POST /content/{id}/publish/github`; `GET /content/{id}/publications`; `POST …/refresh` | Publish disabled until content APPROVED + token configured (already wired). Success → show PR URL. Refresh updates status. |
| 7 | **Other channels** | `GET /content/publish/channels`; `POST /content/{id}/publish {channel, config}` | Render the channel list (`implemented` flag); config form per channel; 502 → readable error. |
| 8 | **Analytics dashboard** | `GET /analytics/summary`, `/trends`, `/content`, `/channels`, `/sources`, `/tracking/status` | Funnel + attribution render; empty states before any data; time-window switch (`?days=`). |
| 9 | **Calendar** | `GET /content` grouped by `due_at` | Overdue/Today/Tomorrow/Later buckets; empty states. |

## Cross-cutting (must-haves, not optional)

- [ ] **Auth guard**: any protected route with no/expired token → redirect to `/login`. Any `401` from the API → clear token + redirect.
- [ ] **Loading / empty / error** states for every data view (no blank screens, no infinite spinners).
- [ ] **No hydration errors** — auth-gated pages are SSR'd; gate client-only state with `useMounted()` (`lib/use-mounted.ts`) + `first-paint.mjs`. Verify a clean console.
- [ ] **Errors are readable**: API returns `{ detail: string }` (422 also `errors[]`); surface `detail`, never `[object Object]`.
- [ ] **Async jobs**: everything `202` (assets, generations, orchestrator) uses the poll-until-terminal pattern.
- [ ] **Tenancy**: never send a tenant id; 404 on someone else's resource is expected — handle gracefully.
- [ ] **Tests** for each changed flow (`*.test.mjs`, `node --test`) — auth redirect, list render, publish form, transition guard.
- [ ] `npm run lint` and `npm run build` green.

## Out of scope for v0.1.0 (do NOT build)

- Marketing homepage, pricing, billing/checkout — not part of this repo.
- API-key management UI, usage dashboard, MCP — backend exists; UI is post-v0.1.0.

## Done =

A recorded 30–60s clip: **login → generate → open GitHub PR**, no errors. That
clip is also the README demo + Show HN asset.
