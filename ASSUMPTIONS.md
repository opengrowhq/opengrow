# ASSUMPTIONS.md — Architectural Decisions & Inference Record

> Every decision here is either derived from the observable feature surface of the
> AI content-generation SaaS reference class (asset uploads, async generation,
> calendar scheduling, multi-brand support, credit metering), or is a scalable
> default chosen where the surface was ambiguous. No proprietary internals were
> reverse-engineered.

---

## 1. Reference class inferences (observable only)

| Observable feature | Design implication |
|---|---|
| Article generation with scheduled publishing to external CMS | Async job queue with cron/scheduler (Celery beat) |
| Multi-brand workspaces (site/brand selector in UI) | Tenant/workspace as first-class boundary |
| Keyword research + article briefs → article generation | Two-stage pipeline; embedding + retrieval-augmented generation |
| Ad / social creative generation (image + text) | Object storage for large assets, not blob-in-DB |
| Brand-style adaptation ("upload your brand assets") | Ingestion pipeline: upload → scan → embed → index |
| Multi-channel calendar (social + email) | Scheduled task fan-out; Celery beat with per-channel routing |
| Usage / credit metering hints | Per-tenant quotas — enforce at rate-limit and job-queue layer |
| Team seats | Membership relation (ReBAC), not just role enum |

Everything below flows from the *superset* of these observable surfaces.

---

## 2. Mandatory stack — accepted

All required components adopted verbatim: Node.js (BFF), Python FastAPI (core),
Celery + Redis + Flower, Qdrant, PostgreSQL, Caddy, LiteLLM, ClamAV, Mailpit.

### AuthZ engine — chose **OpenFGA** over SpiceDB

**Rationale (1 paragraph)**: OpenFGA offers strictly simpler operational overhead
for a single-maintainer OSS project — Docker image runs standalone with a
Postgres data-store, has an official Python SDK (`openfga-sdk`) with a first-class
async client, ships with an interactive playground on port 3000, and the model
DSL round-trips through JSON without external tooling. SpiceDB is more Zanzibar-
faithful (caveats, `watch` API, better handling of huge tenant graphs) but its
sweet spot is >10k-tenant deployments with dedicated platform teams; for a
20-tenant early-alpha we do not need caveats and would pay the operational tax
of Authzed's more opinionated bootstrap. OpenFGA's schema-first model file
(`infra/openfga/model.fga`) also composes cleanly with a Postgres migration
review flow, which matches this repo's Alembic-driven review pattern. If we
outgrow OpenFGA, the Zanzibar semantics port to SpiceDB in a bounded,
well-documented migration.

### Secrets — chose **Infisical** over HashiCorp Vault

Vault's unsealing story adds a boot dance (auto-unseal via cloud KMS / Shamir
shares) that is disproportionate for a one-node Debian deployment. Infisical
runs as a plain Docker container with a Postgres data-store, has both a web UI
and a REST API (used from both Python + Node clients here without SDKs on
either side), and supports machine identity tokens with per-environment scoping.
Rejected: injecting secrets from a cloud KMS provider (AWS Secrets Manager, GCP
Secret Manager, Doppler) — locks the repo to a specific cloud, contradicts the
"self-hostable AGPL OSS" ethos.

---

## 3. Required additions — accepted/rejected

| Addition | Verdict | Justification |
|---|---|---|
| MinIO as S3 upload target | ✅ Accepted | S3-compatible API means the app-side client is portable to any S3 provider (AWS S3, Cloudflare R2, Backblaze B2) with only a hostname change. Postgres BLOB storage is rejected: bloats the DB, breaks streaming, complicates backups. |
| ClamAV before persist | ✅ Accepted | Every upload lands in `MINIO_BUCKET_TEMP`, gets scanned by `scan_asset` Celery task, and is only moved to `MINIO_BUCKET_ASSETS` on `OK`. A `FOUND` verdict leaves the object in the temp bucket and marks the asset `SCAN_FAILED`. |
| Alembic (Python) | ✅ Accepted | Standard for FastAPI + SQLAlchemy 2 async. Migrations in `services/fastapi-core/alembic/versions/`. |
| Node migration tool | ⚠️ Rejected for now | The Node BFF has **zero owned schema** in Postgres (it is a stateless proxy that only verifies JWTs and forwards requests to FastAPI). If the BFF grows a domain that needs schema, we'll adopt `node-pg-migrate`. |
| Multi-tenancy — row-level `tenant_id` | ✅ Accepted | Every tenant-owned table extends `TenantMixin` which mandates `tenant_id`. Every list/get query filters. |
| Postgres RLS (Row Level Security) | ⚠️ **Disabled** | Deliberately not enabled. Two isolation layers already in place: (a) application-layer `tenant_id` filters on every query, (b) OpenFGA authorization checks on every read/write. RLS would add DB-level defense-in-depth but complicates Alembic migrations, breaks Celery worker DSNs (need per-request `SET LOCAL`), and duplicates the OpenFGA decision. If a compliance requirement demands DB-level tenant isolation later, we enable RLS then. |
| LLM abstraction via LiteLLM only | ✅ Accepted | Enforced by convention: no `openai`, `anthropic`, or `google-generativeai` in `requirements.txt`. Every model call routes through `app/core/litellm_client.py`. LiteLLM's model list in `infra/litellm/config.yaml` is the single point of BYOK key management. |
| Async media/generation via Celery | ✅ Accepted | `POST /assets/upload` returns `202 Accepted` with `asset_id` + `scan_job_id`. `POST /generations` returns `202` with `id` + `task_id`. Clients poll `GET /assets/{id}` and `GET /generations/{id}`. SSE/webhook variants are on the roadmap but not in this scaffold. |

---

## 4. Architecture — accepted defaults

### Service split

| Service | Role | Owns |
|---|---|---|
| `node-gateway` | BFF: JWT verify, HTTP proxy, CORS, request size cap | No DB, no state |
| `fastapi-core` | HTTP API, OpenFGA check, DB writes, task dispatch | Postgres, MinIO client, OpenFGA client |
| `celery-worker-light` | Fast tasks: scan, embed, notify | Redis broker `db=0`, results `db=1` |
| `celery-worker-heavy` | Slow tasks: LLM generation | Same broker; separate queue `gen_heavy` |
| `celery-beat` | Periodic: ClamAV sig refresh, future retention sweeps | Redis broker |
| `flower` | Celery observability | Read-only Redis |

### Queue split — `cpu_light` vs `gen_heavy`

`cpu_light` runs at concurrency 4 per worker (scan/embed are I/O-bound after
initial CPU cost); `gen_heavy` runs at concurrency 2 (LLM calls are minutes-long
and hold connections). Prod scale: 2 replicas × 4 concurrency = 8 concurrent
light tasks, 1 replica × 2 concurrency = 2 concurrent heavy tasks. Scale
independently by changing `deploy.replicas`.

### Multi-arch images

All base images verified multi-arch on Docker Hub / Quay / GHCR:
`python:3.13-slim-bookworm`, `node:26-slim`, `postgres:16-alpine`,
`redis:7-alpine`, `qdrant/qdrant:v1.11.3`, `minio/minio:RELEASE.2024-10-29T16-01-48Z`,
`clamav/clamav:1.4`, `openfga/openfga:v1.6.2`, `infisical/infisical:v0.90.1-postgres`,
`ghcr.io/berriai/litellm:main-v1.51.3-stable`, `caddy:2.8-alpine`,
`axllent/mailpit:v1.20`. All support `linux/amd64` + `linux/arm64`.

### Non-root users

Both application Dockerfiles (`services/fastapi-core/Dockerfile`,
`services/node-gateway/Dockerfile`) create `app:app` (uid=gid=1001) and drop
privileges via `USER app`. Infrastructure containers use their upstream defaults
(Postgres/Redis/Qdrant/MinIO run as their own designated non-root users
upstream).

### Healthchecks

Every service in `docker-compose.yml` defines `healthcheck`. Application
services expose `/health` (liveness) and `/ready` (deep check: Postgres, Qdrant,
MinIO, OpenFGA, LiteLLM). `depends_on: { condition: service_healthy }` on every
downstream service.

### 12-factor

- No secrets in git (`.env.example` contains only Infisical connection details)
- No secrets in Dockerfiles (verified: `grep -r 'password\|api_key' services/*/Dockerfile` yields zero hits)
- No secrets in `docker-compose.*.yml` (verified: only `_FILE`-style mount references + `${VAR}` env pass-throughs)
- All service hostnames come from env (`POSTGRES_HOST`, `REDIS_HOST`, ...); no `localhost` anywhere in code

### Connection pooling

- Postgres: SQLAlchemy async engine with `pool_size=10`, `max_overflow=10`,
  `pool_pre_ping=True`, `pool_recycle=1800`. Celery workers use a **sync**
  engine (see `app/workers/tasks.py`) with `pool_size=5` — asyncio in Celery
  tasks is bridged via `_run()` helper that creates a fresh loop per task
  invocation. This avoids the well-known asyncpg-in-Celery event-loop-reuse
  bug where a connection from a prior loop crashes the new one.
- Redis: 3 logical DBs (`0`=broker, `1`=result, `2`=cache); LiteLLM uses `db=4`.
  Client pools handled by `redis-py` and `celery-redis` defaults.

### Backup / restore

`make backup` — dumps every named docker volume to `./backups/<timestamp>/*.tar.gz`
using an ephemeral `alpine` container. `make restore ts=<timestamp>` — reverses
the process. Named volumes: `postgres_data`, `redis_data`, `qdrant_data`,
`minio_data`, `openfga_data`, `infisical_data`, `caddy_data`. Full run
documented in `infra/scripts/backup.sh`.

---

## 5. Deliberate rejections

| Feature | Rejected | Reason |
|---|---|---|
| Blob storage in Postgres | ✅ | Bloats DB, breaks streaming, complicates backups. MinIO is the target. |
| Direct OpenAI/Anthropic SDK imports | ✅ | Enforced by absence from `requirements.txt`. All calls via LiteLLM. |
| Synchronous LLM generation on request thread | ✅ | Would tie up a uvicorn worker for minutes; every LLM request goes to `gen_heavy` queue. |
| Frontend | ⚠️ | A Next.js frontend now exists for login and the tenant app shell. Deeper app flows and browser-level e2e coverage are still pre-alpha. |
| Kubernetes manifests | ✅ | Prod is a single Debian server. K8s is a Month-12+ concern; not in scope. |
| Prometheus + Grafana | ⚠️ | Deferred — Flower covers Celery observability, `/ready` covers liveness. Revisit when the production deployment outgrows single-node observability. |
| RLS on Postgres | ✅ | See row above — two isolation layers already in place. |
| Node-side database schema | ✅ | BFF is stateless; no Node migrations needed today. |

---

## 6. Vertical slice — verification path

The one E2E vertical slice required by the spec, implemented as
`tests/e2e/vertical_slice.sh`:

```
authenticated tenant
  → POST /assets/upload (multipart)         [FastAPI writes DB row, MinIO temp]
  → Celery scan_asset (cpu_light)           [ClamAV verdict → MinIO promote or fail]
  → Celery embed_asset (cpu_light)          [LiteLLM embed → Qdrant upsert]
  → POST /generations (JSON)                [OpenFGA check writer of tenant + reader of asset]
  → Celery run_generation (gen_heavy)       [LiteLLM chat completion → DB result]
  → Celery notify_email (cpu_light)         [SMTP → Mailpit]
  → GET /generations/{id}                   [OpenFGA check reader of generation → 200 result]
```

At `POST /generations` a **different tenant's JWT** returns `403` from OpenFGA
without touching the DB — proving the ReBAC boundary is enforced before data
access.

---

## 7. Environment variables — enumeration

All variables required to run OpenGrow, exhaustively:

**Reachable in `.env.example`** (safe to commit, no secrets):

- `INFISICAL_URL`, `INFISICAL_PROJECT_ID`, `INFISICAL_ENVIRONMENT`, `INFISICAL_TOKEN`
- `OPENGROW_ENV`, `SERVICE_NAME`
- `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_DB`, `POSTGRES_USER`
- `REDIS_HOST`, `REDIS_PORT`, `REDIS_BROKER_DB`, `REDIS_RESULT_DB`, `REDIS_CACHE_DB`
- `QDRANT_HOST`, `QDRANT_PORT`
- `MINIO_HOST`, `MINIO_PORT`, `MINIO_BUCKET_ASSETS`, `MINIO_BUCKET_TEMP`
- `CLAMAV_HOST`, `CLAMAV_PORT`
- `OPENFGA_API_URL`
- `LITELLM_URL`
- `GOOGLE_OAUTH_REDIRECT_URI`
- `MAILPIT_HOST`, `MAILPIT_SMTP_PORT`
- `CADDY_DOMAIN`, `CADDY_EMAIL` (prod only)
- `COOKIE_SECURE` (gateway only: `'true'|'false'`; unset = auto-detect from the request protocol behind Caddy's TLS)

**Pulled from Infisical at boot** (never committed):

- `POSTGRES_PASSWORD`
- `REDIS_PASSWORD` (empty in dev; required in prod)
- `MINIO_ACCESS_KEY`, `MINIO_SECRET_KEY`
- `OPENFGA_STORE_ID`, `OPENFGA_MODEL_ID`
- `LITELLM_MASTER_KEY`
- `JWT_SECRET`
- `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GOOGLE_API_KEY` (optional; BYOK)
- `GOOGLE_OAUTH_CLIENT_ID`, `GOOGLE_OAUTH_CLIENT_SECRET` (optional; GA4/GSC connector OAuth)

---

## 8. Known limits of this scaffold

1. Rate limiting — the *mechanism* is implemented (Redis fixed-window, per
   API-key/token/IP, `app/core/rate_limit.py` + HTTP middleware) but **off by
   default** (`RATE_LIMIT_ENABLED=false`). Per-plan quota enforcement/billing is
   not part of the open-source core.
2. Presigned URL uploads (direct browser → MinIO) — not implemented. Current
   path: browser → node-gateway → FastAPI → MinIO. Fine up to ~25 MiB; larger
   files should switch to presigned PUT.
3. Frontend — present but pre-alpha. The open-source app is login + tenant app
   routes under `/app/[slug]/...` (root `/` redirects to `/login`). Billing
   (Stripe checkout, credits, seat pricing) shipped in 0.2.0 and was removed
   again in 0.3.0 — pricing/billing is not part of the open-source core.
4. WebSocket / SSE — not implemented. Current pattern is client polling; SSE
   for job progress is a candidate future addition.
5. Ollama container — present in `docker-compose.lite.yml` as the in-stack
   `ollama` service (lite default; override `OLLAMA_BASE_URL` to point at the
   host or any other Ollama instance instead).
6. Prometheus / Grafana — not in compose. See rejections.
7. Retention / soft-delete sweep — models have `is_deleted` flag; scheduled
   cleanup task not yet implemented.
8. Refresh token rotation — issued but no server-side revocation store yet.
   Refresh path unimplemented; only access token flow works in this scaffold.
9. Analytics imports — revenue events and aggregate manual/GA4/GSC rows can be
   imported through the protected API with channel normalization and import
   dedupe keys. GA4/GSC connector setup records, Google OAuth start URLs, and
   OAuth callback token exchange exist. Stored connector credentials are redacted
   from API responses. Connector sync attempts fetch and map GSC Search Analytics
   and GA4 Data API landing-page rows into deduped attribution events. Google
   access tokens are refreshed from stored refresh tokens when available, and
   Celery beat enqueues connected connector syncs daily. First-party visit and
   conversion capture exists through public pixel/track endpoints, with protected
   install-status checks, time-windowed reads, previous-period trend deltas, and
   per-content/source/channel trend charts for dashboard setup/executive views.
10. Platform/API layer (implemented, additive): API keys for headless access
    (`X-API-Key` on any endpoint), per-tenant usage metering (`UsageLedger`,
    `/usage`), optional Redis rate limiting, an MCP server (`/mcp`) exposing
    agent tools, multi-channel publishing (WordPress/Ghost/Webflow/Email/X/
    LinkedIn adapters, BYOK, SSRF-guarded), an orchestrator run endpoint
    (generate → promote → optional publish), and optional `limit/offset` +
    `X-Total-Count` pagination on list endpoints. Usage *billing* (charging for
    metered usage) is not part of the open-source core.

---

## 9. Auth transport — Bearer+localStorage (lite) vs httpOnly cookies (gateway)

**Accepted.** The session JWT moves two ways, picked by deployment shape:

- **Lite** (no gateway, browser → fastapi-core directly): access + refresh
  tokens live in localStorage and travel as `Authorization: Bearer …`. Kept
  unchanged — for a personal single-origin deployment the XSS-exfiltration
  exposure of localStorage is an accepted trade-off (see `docs/threat-model.md`),
  and zero cookie machinery keeps the 8-service stack simple.
- **Production** (browser → Caddy → node-gateway BFF → fastapi-core): the
  gateway intercepts the token-issuing responses (`POST /auth/login`,
  `/auth/refresh`, the hosted overlay's `POST /auth/set-password` (its
  responses flow through the gateway's `/auth` proxy), and
  `POST /invites/{token}/accept`),
  moves the tokens into `og_at` (path `/`) and `og_rt` (path `/auth`) cookies —
  `HttpOnly`, `Secure` (pinned via `COOKIE_SECURE` or auto-detected from the
  request protocol with `trustProxy: true`), `SameSite=Strict`, `Max-Age` from
  the JWT `exp` claim — and strips them from the JSON body, marking the
  response `x-og-auth: cookie` so the frontend knows which transport is live.
  On the way in, an `onRequest` hook (registered before the edge-auth hook)
  re-injects `og_at` as the Bearer header, so the edge JWT verify is untouched.
  `/auth/refresh` additionally gets the `og_rt` value injected into the proxied
  JSON body (the browser cannot read the httpOnly cookie to send it itself).

**Rationale.** Tokens in browser-readable storage are one XSS payload away
from full account compromise. httpOnly cookies remove the entire token-
exfiltration class for production multi-tenant deployments while keeping the
gateway stateless (no server-side session store — the JWT still carries
identity, the cookie is only a transport).

**What stays the same.** Edge JWT verification in the gateway; fastapi-core
unchanged except `allow_credentials=True` on CORS (origins stay the explicit
`settings.cors_origins` list — never reflect + credentials); the frontend's
Bearer+localStorage flow untouched in lite mode (the cookie-mode flag only
flips when the gateway's mode header is seen).

**Local gateway routes.** `POST /auth/logout` (expires both cookies) and
`POST /auth/session` — a fixation-guarded (`X-Requested-With` required,
30/min/IP), deliberately token-unvalidated one-shot handoff so OAuth-callback
fragments (`/login#access_token=…`) can move into httpOnly cookies without
passing through JS-readable storage. Not validating there is acceptable: the
edge auth check validates the cookie on the next proxied request, so a forged
session buys nothing a bad Bearer header wouldn't.

**Rejected alternatives.**
- *Tokens in sessionStorage* — same exfiltration class as localStorage; only
  narrows persistence, doesn't remove the threat.
- *Stripping tokens from response bodies without a mode header* — the
  frontend could not distinguish a gateway-stripped login from a broken lite
  login; the explicit `x-og-auth` header keeps both transports detectable and
  lets lite behavior stay byte-identical.
