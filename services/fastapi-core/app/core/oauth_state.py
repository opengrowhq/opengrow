"""Single-use OAuth state tokens (Redis-backed, 10-minute TTL).

The auth-url endpoint issues a state that the callback endpoint must consume
exactly once, binding the consent redirect to the tenant/user/provider that
started it. Previously the state was generated and returned but never stored,
so it could not be validated.
"""

from __future__ import annotations

import json
import secrets

from app.config import settings

_TTL_SECONDS = 600
_PREFIX = "oauth_state:"


def _client():
    # No cross-call caching: redis.asyncio clients bind to the event loop that
    # created them, and pytest (like any multi-loop host) would hand us a
    # client bound to a closed loop. A fresh client per call is cheap here.
    import redis.asyncio as aioredis

    return aioredis.from_url(settings.redis_cache_url)


async def issue_oauth_state(*, provider: str, tenant_id: str, user_id: str) -> str:
    state = secrets.token_urlsafe(24)
    payload = json.dumps(
        {"provider": provider, "tenant_id": tenant_id, "user_id": user_id}
    )
    await _client().set(_PREFIX + state, payload, ex=_TTL_SECONDS)
    return state


async def consume_oauth_state(state: str) -> dict | None:
    """Return the stored payload exactly once; None when unknown or expired."""
    raw = await _client().getdel(_PREFIX + state)
    if not raw:
        return None
    return json.loads(raw)
