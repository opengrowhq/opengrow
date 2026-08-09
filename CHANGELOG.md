# Changelog

All notable changes to OpenGrow are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project aims to
follow [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
