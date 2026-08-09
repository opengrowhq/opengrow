"""Infisical client — pulls secrets at process boot (production mode only)."""

from __future__ import annotations
import logging

log = logging.getLogger("secrets")

_REQUIRED = {
    "POSTGRES_PASSWORD",
    "MINIO_ACCESS_KEY",
    "MINIO_SECRET_KEY",
    "OPENFGA_STORE_ID",
    "OPENFGA_MODEL_ID",
    "LITELLM_MASTER_KEY",
    "JWT_SECRET",
}


def fetch_secrets(
    url: str, project_id: str, environment: str, token: str
) -> dict[str, str]:
    """Called only in DEPLOYMENT_MODE=production. Lite mode reads env vars directly."""
    if not token:
        log.warning(
            "INFISICAL_TOKEN empty — using pydantic-settings defaults (dev-only path)"
        )
        return {}
    try:
        from infisical_client import InfisicalClient, ClientSettings, ListSecretsOptions
    except Exception as e:  # pragma: no cover
        log.warning("infisical_client unavailable (%s) — using defaults", e)
        return {}

    try:
        client = InfisicalClient(
            ClientSettings(
                access_token=token,
                site_url=url,
            )
        )
        secrets = client.listSecrets(
            options=ListSecretsOptions(
                environment=environment,
                project_id=project_id,
            )
        )
        out: dict[str, str] = {}
        for s in secrets:
            out[s.secret_key] = s.secret_value
        missing = _REQUIRED - out.keys()
        if missing:
            log.error(
                "Infisical missing required secrets: %s", ",".join(sorted(missing))
            )
        return out
    except Exception as e:  # pragma: no cover
        log.error("Infisical fetch failed: %s", e)
        return {}
