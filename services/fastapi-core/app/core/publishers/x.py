"""X (Twitter) publisher — API v2, OAuth2 user-context token (BYOK).

config: { access_token }  # OAuth2 user-context bearer with tweet.write scope
Posts the content as a tweet (truncated to 280 chars). The token must be a
USER-context token (app-only bearer can't post) — that's the caller's OAuth app.
Docs: https://developer.x.com/en/docs/x-api/tweets/manage-tweets
"""

from __future__ import annotations

import httpx

from app.core.publishers.base import PublisherError, PublishResult

_API = "https://api.twitter.com/2/tweets"


def build_payload(body: str) -> dict:
    return {"text": body.strip()[:280]}


async def publish(*, title: str, body: str, config: dict) -> PublishResult:
    token = config.get("access_token")
    if not token:
        raise PublisherError("X config missing: access_token (OAuth2 user token)")
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.post(
                _API,
                json=build_payload(body),
                headers={"Authorization": f"Bearer {token}"},
            )
    except httpx.HTTPError as e:
        raise PublisherError(f"X request failed: {e}") from e
    if resp.status_code >= 400:
        raise PublisherError(f"X error {resp.status_code}: {resp.text[:200]}")
    tweet_id = (resp.json().get("data") or {}).get("id", "")
    return {
        "url": f"https://x.com/i/web/status/{tweet_id}" if tweet_id else "",
        "external_ref": f"tweet {tweet_id}",
    }
