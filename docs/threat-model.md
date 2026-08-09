# Lite vs Production threat model

OpenGrow ships in two shapes from one codebase. They make **different security
assumptions**. [`SECURITY.md`](../SECURITY.md) covers reporting and policy; this
doc covers what actually changes between the two deployments.

## TL;DR

**Lite mode is for a single trusted operator on a trusted network (your laptop
or a private VPS). Do not expose lite mode to the public internet or to
untrusted users.** Production mode is the multi-tenant, hardened deployment.

## What changes between modes

Lite (`docker-compose.lite.yml`, `DEPLOYMENT_MODE=lite`) deliberately drops
several production components in exchange for a ~5-minute, ~2 GB setup:

| Concern | Lite | Production |
|---|---|---|
| **Authorization (ReBAC)** | OpenFGA stubbed — the authorizer **allows all** within the single tenant | OpenFGA enforces per-tenant relationship checks |
| **Secrets** | Plain env vars in `.env` | Infisical-managed secrets |
| **Upload scanning** | ClamAV **skipped** — `scan_bytes()` returns `skipped-lite-mode` (operator trusts their own uploads) | ClamAV streams every upload; `FOUND`/`ERROR` → `SCAN_FAILED`, file never leaves the temp bucket |
| **Vector store** | Embeddings stored on the Postgres row, ranked in-DB | Qdrant, plus the Postgres mirror |
| **LLM routing** | LiteLLM runs **in-process** (`LITELLM_MODE=library`) | LiteLLM proxy service |
| **API edge** | FastAPI bound **directly** on `127.0.0.1:8000` | node-gateway BFF + Caddy TLS in front |
| **Async workers** | One worker (`cpu_light,gen_heavy`) | Split queues, beat, flower |

## What stays the same

- **Authentication** — JWT bearer auth (`/auth/login`) in both modes; API keys
  (`X-API-Key`) for headless access.
- **Tenant scoping** — every query is tenant-scoped in the application layer in
  both modes. In lite there is effectively one tenant and the ReBAC layer does
  not add defense-in-depth on top of that.
- **Provider data flow** — model calls route through LiteLLM in both modes; see
  [model-provider-data-flow.md](./model-provider-data-flow.md).

## Network exposure assumptions

- The lite compose publishes every port on **`127.0.0.1` only** (Postgres,
  Redis, MinIO, Mailpit, FastAPI, frontend). Nothing binds `0.0.0.0` by default.
- Default lite credentials (`*-lite-change-me`, `JWT_SECRET=change-me-…`) are
  **development placeholders**. Change them before putting lite on any shared
  host.

## What lite mode is NOT safe for

- **Public-internet exposure** without a reverse proxy, TLS, real secrets, and
  rate limiting.
- **Multi-user / multi-tenant** use — the authorizer allows all within the
  tenant and uploads are not malware-scanned.
- **Untrusted uploads** — with ClamAV skipped, an uploaded file is trusted. Only
  upload content you trust.

If you need any of the above, run the production stack (`make prod-up`) or put
lite behind your own hardened edge and replace all placeholder secrets.
