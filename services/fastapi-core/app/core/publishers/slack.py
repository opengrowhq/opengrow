"""Slack publisher — Incoming Webhook, BYOK.

config: { webhook_url }  # https://api.slack.com/messaging/webhooks
Posts the content as a message to the configured channel. No external ID or
permalink is returned by the webhook API, so `url`/`external_ref` are empty.
Docs: https://api.slack.com/messaging/webhooks
"""

from __future__ import annotations

import httpx

from app.core.publishers.base import PublisherError, PublishResult
from app.core.publishers.safety import safe_url

REQUIRED = ("webhook_url",)
_MAX_TEXT = 3000  # Slack's practical block/text length guidance


def build_payload(title: str, body: str) -> dict:
    text = f"*{title}*\n{body}" if title else body
    return {"text": text.strip()[:_MAX_TEXT]}


async def publish(*, title: str, body: str, config: dict) -> PublishResult:
    missing = [k for k in REQUIRED if not config.get(k)]
    if missing:
        raise PublisherError(f"Slack config missing: {', '.join(missing)}")
    webhook_url = config["webhook_url"]
    safe_url(webhook_url)  # SSRF guard: block internal/metadata hosts
    try:
        async with httpx.AsyncClient(timeout=20, follow_redirects=False) as client:
            resp = await client.post(webhook_url, json=build_payload(title, body))
    except httpx.HTTPError as e:
        raise PublisherError(f"Slack request failed: {e}") from e
    if resp.status_code >= 400:
        raise PublisherError(f"Slack error {resp.status_code}: {resp.text[:200]}")
    return {"url": "", "external_ref": ""}
