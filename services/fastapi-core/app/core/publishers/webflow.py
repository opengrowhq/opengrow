"""Webflow publisher — CMS API v2, Bearer token (BYOK).

config: { api_token, collection_id, body_field?, status? }
Creates a CMS item; field slugs are collection-specific, so `body_field`
(default "post-body") maps the content into your rich-text field.
Docs: https://developers.webflow.com/data/reference/create-collection-item
"""

from __future__ import annotations

import re

import httpx

from app.core.publishers.base import PublisherError, PublishResult

REQUIRED = ("api_token", "collection_id")
_API = "https://api.webflow.com/v2"


def _slug(title: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:256] or "post"


def build_item(title: str, body: str, body_field: str = "post-body") -> dict:
    return {
        "isDraft": False,
        "fieldData": {"name": title, "slug": _slug(title), body_field: body},
    }


async def publish(*, title: str, body: str, config: dict) -> PublishResult:
    missing = [k for k in REQUIRED if not config.get(k)]
    if missing:
        raise PublisherError(f"Webflow config missing: {', '.join(missing)}")
    item = build_item(title, body, config.get("body_field", "post-body"))
    url = f"{_API}/collections/{config['collection_id']}/items"
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.post(
                url,
                json=item,
                headers={"Authorization": f"Bearer {config['api_token']}"},
            )
    except httpx.HTTPError as e:
        raise PublisherError(f"Webflow request failed: {e}") from e
    if resp.status_code >= 400:
        raise PublisherError(f"Webflow error {resp.status_code}: {resp.text[:200]}")
    data = resp.json()
    return {"url": "", "external_ref": f"item {data.get('id', '')}"}
