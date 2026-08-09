# OpenGrow — Project Instructions for AI Assistants

> **Source of truth for every AI agent** (Claude, Codex, Kimi, Hermes) working on this repo.
> `CLAUDE.md`, if present, should only load this file — do not duplicate rules.

## Before any change

Read in this order:

1. `AGENTS.md` (this file)
2. `ASSUMPTIONS.md` — architectural decisions + rejections
3. The relevant source files under `services/`
4. `README.md` for cross-cutting context

## Project overview

OpenGrow is an open-source (AGPL v3) multi-tenant AI content-generation SaaS.
Self-host free, paid hosted tier on `opengrow.dev`.

- **License**: AGPL v3 (community) + commercial option per NOTICE
- **Domain**: opengrow.dev (owned)
- **Status**: Pre-alpha. Backend + Next.js web app shipped (login, brand onboarding, content library/editor, calendar, dashboard, AI generation studios).

## Two deployment modes — pick by env var

The same `services/fastapi-core/app/` code runs in either mode. `DEPLOYMENT_MODE` env var switches the boot-time wiring:

- **`DEPLOYMENT_MODE=lite`** (personal use, 5 services) — env-var secrets, stub OpenFGA (`check → True`), ClamAV skipped, LiteLLM as Python library, no Qdrant persistence, direct FastAPI (no BFF). Compose: `docker-compose.lite.yml`. See `Makefile`: `lite-up`, `lite-migrate`, `lite-seed`.
- **`DEPLOYMENT_MODE=production`** (multi-tenant / hosted, 15 services) — Infisical secrets, real OpenFGA, ClamAV enforced, LiteLLM proxy container, Qdrant, node-gateway BFF, Caddy. Compose: `docker-compose.yml` (+ dev / prod overlays).

Every core module that has a lite path documents both branches. When adding a new capability, decide explicitly: is this personal-use-safe (implement lite path or graceful skip), or hosted-only (guard with `if not settings.is_lite: ...`)?

Full rationale in `ASSUMPTIONS.md`.

## Tech stack (mandatory — do not substitute)

| Layer | Choice | Notes |
|---|---|---|
| BFF | Node.js 22 + Fastify + TypeScript | Stateless JWT verifier + HTTP proxy |
| Core | Python 3.12 + FastAPI + SQLAlchemy 2 async + Alembic | All business logic + DB |
| Queue | Celery 5 + Redis 7 + Flower | Two queues: `cpu_light`, `gen_heavy` |
| DB | PostgreSQL 16 | Multi-tenant via row-level `tenant_id` |
| Vector | Qdrant 1.11 | One collection per resource type |
| Object storage | MinIO | Tenant-prefixed keys |
| AuthZ | OpenFGA (Zanzibar-style ReBAC) | See `ASSUMPTIONS.md` for why not SpiceDB |
| Secrets | Infisical | Never in git/compose/Dockerfiles |
| LLM gateway | LiteLLM | ALL model calls route through here — never import `openai`/`anthropic` directly |
| AV | ClamAV (clamd network socket) | Scan every upload before persist |
| Local mail | Mailpit | Dev only; prod uses SMTP-relay via LiteLLM/SendGrid |
| Reverse proxy | Caddy v2 | Auto-TLS in prod |
| Orchestration | docker compose | Base + dev overlay + prod overlay |

## Critical patterns (quick reference)

### Multi-tenancy
- Every tenant-owned table extends `TenantMixin` in `app/models/base.py`
- Every list/get query filters `.where(Model.tenant_id == current.tenant_id)`
- Every mutation/read of a tenant-owned resource calls `authz_client.check(...)` before touching DB
- OpenFGA relations bound at resource creation via `authz_client.bind_resource_to_tenant(...)`

### Async job flow
- HTTP handlers return `202 Accepted` with a job/task ID
- Client polls a status endpoint until terminal state
- Long-running work runs in Celery workers on the appropriate queue
- Cross-task chaining: task A ends by calling `task_b.delay(entity_id)` (see `scan_asset → embed_asset`)

### Asset pipeline (invariant)
```
upload → MinIO temp bucket → scan_asset (Celery) → ClamAV
  → clean? → promote to assets bucket → embed_asset (Celery)
    → LiteLLM embed → Qdrant upsert → status=INDEXED
  → infected? → status=SCAN_FAILED, temp object left in place for audit
```

### LLM abstraction (invariant)
- **Never** `import openai`, `import anthropic`, `import google.generativeai` in `services/fastapi-core/app/`
- Every model call goes through `app/core/litellm_client.py`
- Model routing configured in `infra/litellm/config.yaml`
- BYOK keys pulled from Infisical at LiteLLM boot

### Secrets (invariant)
- No credentials in git — verified: `grep -r password\|api_key\|secret Dockerfile docker-compose.yml docker-compose.prod.yml` returns zero non-`_FILE`, non-`${}` hits
- `.env.example` contains only Infisical connection details
- Runtime secrets fetched by `app/core/secrets.py` on process boot
- Dev bootstrap: `make bootstrap` seeds `./infra/secrets/*` files (git-ignored)

### Dependency freshness / CVE policy (invariant)
- **Use the latest stable release** of every dependency, base image, and tool at
  the time work is done — do not pin to a known-outdated version. Resolve
  "latest" at implementation time (check the registry / release notes); never
  copy a version number from an older doc or from model memory.
- **Zero open CVEs at merge.** Dependabot alerts must be at zero and
  `pip-audit` / `npm audit` clean before a PR merges. A dependency with an
  unpatched advisory blocks the merge — upgrade, replace, or remove it.
- **New deps must be actively maintained** — a recent release, live issue
  tracker, no archived/deprecated status. Prefer a maintained library over an
  abandoned one even if the abandoned one fits slightly better.
- **Base images**: track the latest stable minor of the pinned major
  (Python 3.12.x, Node 22.x, Postgres 16.x, Redis 7.x, …) and rebuild so
  security patches land; bump the major deliberately, not by drift.
- Dependabot (grouped) + CI `audit` steps are the enforcement mechanism — keep
  them green; do not merge past a red security job.

### Money
- Not applicable in the scaffold (no billing yet). When billing lands:
  amounts as integer cents, currency EUR by default.

### Events / audit
- Not implemented in scaffold. On next round: publish domain events via a Redis pub/sub
  bus after every DB mutation; audit rows in a shared `audit_log` table.

## Key commands

**Lite (5 services)**:
```bash
make lite-up       # Start lite stack (postgres, redis, minio, fastapi-core, celery-worker, mailpit)
make lite-migrate  # Alembic migrations
make lite-seed     # Demo tenant + user
make lite-down     # Stop (keep data)
make lite-shell    # Bash into fastapi-core
```

**Production (15 services)**:
```bash
make bootstrap    # One-time: generate secret files, seed dev Infisical, bring up deps
make up-d         # Start full dev stack (background)
make migrate      # Run Alembic migrations
make seed         # Seed demo tenant + user + OpenFGA membership
make test-e2e    # Run tests/e2e/vertical_slice.sh (full pipeline)
make prod-up      # Prod bring-up (Debian, requires DNS + Caddy env vars)
make down         # Stop stack (keep volumes)
```

**Shared**:
```bash
make lint         # Ruff (backend) + ESLint (gateway)
make format       # Ruff format + Prettier
make shell        # Bash into fastapi-core container (full stack)
make db-shell     # psql into postgres
make backup       # Backup all named volumes to ./backups/<timestamp>/
```

## Directory conventions

```
services/fastapi-core/app/
├── core/         # Cross-cutting: authz, auth, litellm, minio, qdrant, clamav, secrets
├── models/       # SQLAlchemy 2 models — every tenant-owned table uses TenantMixin
├── schemas/      # Pydantic v2 request/response models
├── routers/      # Thin — parse, authz check, delegate to services/tasks
└── workers/      # Celery tasks — always @celery.task(name="app.workers.tasks.<name>")

services/node-gateway/src/
├── config.ts     # Loads Infisical secrets at boot
├── infisical.ts  # Minimal REST client (no SDK)
├── middleware/   # JWT verify (currently only auth)
├── routes/       # Local routes (currently only /health, /ready)
└── server.ts     # Fastify bootstrap + reverse proxy registration
```

## Endpoint conventions

- `GET /health` — liveness (no dependency check)
- `GET /ready` — readiness (deep check: DB + Qdrant + MinIO + OpenFGA + LiteLLM)
- Trailing slash NOT required in FastAPI 0.115+ — use `""` for base or `/<path>`
- Auth: `Depends(get_current_user)` on every protected endpoint. It accepts a
  Bearer JWT **or** an `X-API-Key` header (see `app/core/api_keys.py`), so keep
  new endpoints auth-agnostic — never assume JWT.
- Authz: explicit `authz_client.check(user_id, relation, object)` — no framework-level wrapper yet (add in Phase 4)
- List endpoints: use `Depends(pagination)` + `paginate()` (`app/core/pagination.py`)
  to add optional `limit/offset` + `X-Total-Count` without changing the array response.
- Meter billable actions with `record_usage()` (`app/core/usage.py`); the ledger
  is open-source, but usage *billing/quota enforcement* is a hosted concern only.
- Publishing channels go through the adapter registry (`app/core/publishers/`);
  each adapter is plain httpx + BYOK, mirroring `github_publisher.py`.

## Testing

- Every new or changed functionality must include focused tests in the same change.
- Cover the user-visible behavior or contract being changed, not only implementation details.
- Bug fixes must include a regression test when the failure mode is reproducible.
- If an automated test is not practical in the touched layer, add the closest useful lower-level test and call out the remaining gap.
- Backend: `pytest --tb=short` inside `fastapi-core` container
- Frontend: `npm test` and `npm run lint` inside `services/frontend` or the `frontend` container
- Gateway: `npm test` (node --test) inside `node-gateway` container
- E2E: `bash tests/e2e/vertical_slice.sh` — full pipeline against the live dev stack

## Git workflow

Branch strategy — `main` / `dev` / `feature/*`:

```
feature/*    ← daily work, short-lived, one focused change
    ↓ PR (self-merge, 0 approvals needed)
dev          ← integration branch, less strict protection
    ↓ PR (when stable batch ready for release)
main         ← tagged releases only, strict protection, no force pushes
```

**Rules**:
- `main` is protected — do not branch daily work off it, do not PR feature branches directly to it
- `dev` is the daily default — all feature branches start from `dev` and PR back into `dev`
- `main ← dev` PRs happen only at release time (tag v0.x.y after merge)
- Commits: conventional (`feat:`, `fix:`, `chore:`, `docs:`, `refactor:`)
- Never commit `.env`, `infra/secrets/*`, `backups/*` (all in `.gitignore`)
- Never push without explicit user request

**Typical feature flow**:
```bash
git checkout dev && git pull
git checkout -b feature/frontend-scaffold
# ...work + commit...
git push -u origin feature/frontend-scaffold
# open PR on GitHub: base=dev, compare=feature/frontend-scaffold
# self-merge (0 approvals required on dev)
```

**Release flow**:
```bash
# Once dev has accumulated stable changes:
# open PR on GitHub: base=main, compare=dev
# merge, then locally:
git checkout main && git pull
git tag v0.1.0 && git push origin v0.1.0
# create release notes on GitHub Releases
```

## Documentation cadence

At the end of every meaningful change to the code:
1. Update `README.md` if user-facing behavior changed (env vars, commands, endpoints)
2. Update `ASSUMPTIONS.md` if an architectural decision was accepted or rejected
3. Update this file (`AGENTS.md`) if patterns, conventions, or invariants changed

## Security checklist (every PR)

- [ ] Every new endpoint uses `get_current_user`
- [ ] Every DB query filters by `tenant_id`
- [ ] Every mutation/read of tenant-owned data calls `authz_client.check`
- [ ] No `openai`/`anthropic`/`google-generativeai` imports outside `litellm_client.py`
- [ ] No new secrets in git — all pulled from Infisical
- [ ] Input validated with Pydantic schemas
- [ ] Uploads: content-type allowlist, size cap, ClamAV scan before persist
- [ ] New/changed deps are latest-stable, actively maintained, zero open CVEs (Dependabot + `pip-audit`/`npm audit` green)

## Restricted files

Never read or modify:
- `.env` (the actual runtime file)
- `infra/secrets/*` (real secret values)
- `backups/*` (may contain PII)
