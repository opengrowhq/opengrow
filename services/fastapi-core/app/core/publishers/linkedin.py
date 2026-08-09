"""LinkedIn publisher — UGC Posts API, OAuth2 token (BYOK).

config: { access_token, author_urn }  # e.g. "urn:li:person:XXXX" or org URN
Posts the content as a text share. Token needs w_member_social (or org) scope —
the caller's OAuth app.
Docs: https://learn.microsoft.com/en-us/linkedin/marketing/community-management/shares/ugc-post-api
"""

from __future__ import annotations

import httpx

from app.core.publishers.base import PublisherError, PublishResult

REQUIRED = ("access_token", "author_urn")
_API = "https://api.linkedin.com/v2/ugcPosts"


def build_payload(author_urn: str, body: str) -> dict:
    return {
        "author": author_urn,
        "lifecycleState": "PUBLISHED",
        "specificContent": {
            "com.linkedin.ugc.ShareContent": {
                "shareCommentary": {"text": body.strip()},
                "shareMediaCategory": "NONE",
            }
        },
        "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"},
    }


async def publish(*, title: str, body: str, config: dict) -> PublishResult:
    missing = [k for k in REQUIRED if not config.get(k)]
    if missing:
        raise PublisherError(f"LinkedIn config missing: {', '.join(missing)}")
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.post(
                _API,
                json=build_payload(config["author_urn"], body),
                headers={
                    "Authorization": f"Bearer {config['access_token']}",
                    "X-Restli-Protocol-Version": "2.0.0",
                },
            )
    except httpx.HTTPError as e:
        raise PublisherError(f"LinkedIn request failed: {e}") from e
    if resp.status_code >= 400:
        raise PublisherError(f"LinkedIn error {resp.status_code}: {resp.text[:200]}")
    post_id = resp.json().get("id", "") or resp.headers.get("x-restli-id", "")
    return {"url": "", "external_ref": f"post {post_id}"}
