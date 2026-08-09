"""WordPress publisher — REST API v2, Application-Password auth (BYOK).

config: { site_url, username, app_password, status? }
Docs: https://developer.wordpress.org/rest-api/reference/posts/
"""

from __future__ import annotations

import httpx

from app.core.publishers.base import PublisherError, PublishResult
from app.core.publishers.safety import safe_url

REQUIRED = ("site_url", "username", "app_password")


def build_payload(title: str, body: str, status: str = "publish") -> dict:
    return {"title": title, "content": body, "status": status}


def _endpoint(site_url: str) -> str:
    return f"{site_url.rstrip('/')}/wp-json/wp/v2/posts"


async def publish(*, title: str, body: str, config: dict) -> PublishResult:
    missing = [k for k in REQUIRED if not config.get(k)]
    if missing:
        raise PublisherError(f"WordPress config missing: {', '.join(missing)}")
    safe_url(config["site_url"])  # SSRF guard: block internal/metadata hosts
    status = config.get("status", "publish")
    try:
        async with httpx.AsyncClient(timeout=20, follow_redirects=False) as client:
            resp = await client.post(
                _endpoint(config["site_url"]),
                json=build_payload(title, body, status),
                auth=(config["username"], config["app_password"]),
            )
    except httpx.HTTPError as e:
        raise PublisherError(f"WordPress request failed: {e}") from e
    if resp.status_code >= 400:
        raise PublisherError(f"WordPress error {resp.status_code}: {resp.text[:200]}")
    data = resp.json()
    return {"url": data.get("link", ""), "external_ref": f"post {data.get('id', '')}"}
