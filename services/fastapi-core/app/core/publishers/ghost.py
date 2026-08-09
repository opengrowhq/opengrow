"""Ghost publisher — Admin API, JWT auth from an admin API key (BYOK).

config: { admin_api_url, admin_api_key ("id:secret"), status? }
Docs: https://ghost.org/docs/admin-api/#token-authentication
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import httpx
import jwt

from app.core.publishers.base import PublisherError, PublishResult
from app.core.publishers.safety import safe_url

REQUIRED = ("admin_api_url", "admin_api_key")


def build_token(admin_api_key: str, now: datetime | None = None) -> str:
    """Ghost Admin JWT: HS256 signed with the hex secret, kid = key id."""
    try:
        key_id, secret = admin_api_key.split(":", 1)
    except ValueError as e:
        raise PublisherError("Ghost admin_api_key must be 'id:secret'") from e
    issued = now or datetime.now(timezone.utc)
    return jwt.encode(
        {
            "iat": int(issued.timestamp()),
            "exp": int((issued + timedelta(minutes=5)).timestamp()),
            "aud": "/admin/",
        },
        bytes.fromhex(secret),
        algorithm="HS256",
        headers={"kid": key_id},
    )


def build_payload(title: str, html: str, status: str = "published") -> dict:
    return {"posts": [{"title": title, "html": html, "status": status}]}


async def publish(*, title: str, body: str, config: dict) -> PublishResult:
    missing = [k for k in REQUIRED if not config.get(k)]
    if missing:
        raise PublisherError(f"Ghost config missing: {', '.join(missing)}")
    safe_url(config["admin_api_url"])  # SSRF guard: block internal/metadata hosts
    token = build_token(config["admin_api_key"])
    url = f"{config['admin_api_url'].rstrip('/')}/ghost/api/admin/posts/?source=html"
    try:
        async with httpx.AsyncClient(timeout=20, follow_redirects=False) as client:
            resp = await client.post(
                url,
                json=build_payload(title, body, config.get("status", "published")),
                headers={
                    "Authorization": f"Ghost {token}",
                    "Accept-Version": "v5.0",
                },
            )
    except httpx.HTTPError as e:
        raise PublisherError(f"Ghost request failed: {e}") from e
    if resp.status_code >= 400:
        raise PublisherError(f"Ghost error {resp.status_code}: {resp.text[:200]}")
    posts = resp.json().get("posts", [])
    post = posts[0] if posts else {}
    return {"url": post.get("url", ""), "external_ref": f"post {post.get('id', '')}"}
