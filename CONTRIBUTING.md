# Contributing to OpenGrow

OpenGrow is an AGPL-licensed, self-hostable AI content marketing platform. The first contribution goal is simple: make the GitHub-native content workflow real, easy to run, and easy to trust.

## Start here

1. Read [README.md](./README.md) for product context.
2. Read [ROADMAP.md](./ROADMAP.md) for what is being built next.
3. Use lite mode for local development unless you are working on production-only infrastructure.

## 15-minute lite setup

```bash
cp .env.lite.example .env
make lite-up
make lite-migrate
make lite-seed
make seed-demo   # optional: load examples/ fixtures (brand context, content, attribution)
```

Then open:

- `http://127.0.0.1:3000` for the frontend.
- `http://127.0.0.1:8000/docs` for the FastAPI docs.

Log in with:

- Email: `demo@opengrow.dev`
- Password: `123456`

Run the current backend vertical slice:

```bash
GW=http://127.0.0.1:8000 bash tests/e2e/vertical_slice.sh
```

Frontend app routes are tenant-scoped. After login, the demo user should land at `/app/demo`; protected app pages must live under `/app/[slug]/...`, not at top-level paths like `/content` or `/brand`.

## Good first contributions

Good first issues should be scoped, testable, and not require real secrets. See the [good first issue backlog](docs/good-first-issues.md) for ready-to-pick issues with acceptance criteria, and the [Hacktoberfest kit](docs/hacktoberfest.md).

Best areas:

- Documentation examples.
- Demo data.
- Markdown export templates.
- Frontend states.
- Tests for existing endpoints.
- Publisher adapter scaffolds.
- Analytics import examples.

Avoid first contributions that touch tenant isolation, auth, production secrets, or deployment hardening unless a maintainer has already scoped the issue.

## Development rules

- Keep self-hosted functionality complete — the full feature set ships in the open-source core, never withheld.
- Never commit `.env`, `infra/secrets/*`, `backups/*`, API keys, passwords, or real customer data.
- All model calls must go through `services/fastapi-core/app/core/litellm_client.py`.
- Every tenant-owned table must include `tenant_id`.
- Protected endpoints must use `get_current_user`.
- Tenant-owned reads and writes must check authorization.
- Long-running jobs should use Celery and return `202 Accepted` from HTTP.
- Every new or changed functionality must include focused tests in the same change.
- Prefer automated tests over manual validation; when a full harness is missing, add the closest useful lower-level test and document the gap.

## Pull request checklist

- [ ] The change has a clear issue or problem statement.
- [ ] Lite mode still works or the feature is explicitly production-only.
- [ ] Focused tests are included for the changed behavior, or the remaining test gap is explicitly documented.
- [ ] User-facing behavior is documented.
- [ ] No secrets or private data are committed.
- [ ] Security-sensitive changes explain the trust boundary.

## Build-in-public expectation

Meaningful features should produce:

- GitHub issue.
- Pull request.
- Release note.
- Demo artifact.
- Documentation update.

Use the [ship checklist](docs/ship-checklist.md) for each feature and the [release checklist](docs/release-checklist.md) for each release.

This is not paperwork. It is how OpenGrow turns open-source shipping into distribution.
