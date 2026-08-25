# Security

OpenGrow is pre-alpha. Do not use it with sensitive production data unless you have reviewed the code, deployment mode, and operational controls.

## Reporting vulnerabilities

Report security issues privately via [GitHub Security Advisories](https://github.com/opengrowhq/opengrow/security/advisories/new) — do not email or open a public issue. Please include:

- Affected version or commit.
- Reproduction steps.
- Expected impact.
- Any suggested fix.

Do not open a public issue for exploitable vulnerabilities.

## Security posture

OpenGrow is designed around auditability and self-hosted control:

- Source code is available under AGPL v3.
- Enterprises that cannot use AGPL can request a commercial license.
- Model calls are routed through LiteLLM; application code must not call provider SDKs directly.
- Production mode uses OpenFGA authorization checks.
- Tenant-owned data uses `tenant_id` at the model/query layer.
- Uploads go through object storage and are scanned by ClamAV in production mode before promotion.
- Secrets are loaded from Infisical in production mode and must not be committed.
- Backup and restore scripts exist for named Docker volumes.

## Lite vs production mode

Lite mode is for personal use and quick evaluation. It intentionally skips some production controls:

- AuthZ is stubbed to allow access.
- ClamAV scanning is skipped.
- Qdrant persistence is skipped.
- Secrets are read from env vars.
- FastAPI is accessed directly.

Production mode enables the full trust boundary:

- OpenFGA authorization.
- ClamAV scanning.
- Qdrant persistence.
- Infisical-managed secrets.
- Node/Fastify gateway.
- Caddy reverse proxy.

## Secret handling

Never commit:

- `.env`
- `infra/secrets/*`
- `backups/*`
- Provider API keys.
- JWT secrets.
- Database passwords.
- Customer uploads or exports.

## Model-provider data flow

OpenGrow sends prompts, selected brand context, and generation inputs to the configured model provider through LiteLLM. Self-hosted operators control the keys and providers they configure. Hosted mode will document managed-provider behavior before production launch.

## Current known limits

- Refresh token revocation is not yet implemented.
- Rate limiting exists (`app/core/rate_limit.py`, Redis fixed-window) but is off by default (`RATE_LIMIT_ENABLED=false`) — enable it for any internet-facing deployment.
- Audit logging covers login (success/failure), API key create/revoke, GitHub credential connect/disconnect, and content publish, via `GET /audit`. Coverage does not yet include tenant-settings or role/team-management actions — those features don't exist yet either.
- SOC 2 / ISO controls are not yet in place.
- Lite mode is not a production security profile.
