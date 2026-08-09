"""Redis fixed-window rate limiter (per API-key / token / IP).

Disabled unless settings.RATE_LIMIT_ENABLED; the middleware short-circuits so
lite/self-host pays nothing. Groundwork for per-tenant quotas on the hosted API.
"""

from __future__ import annotations

import hashlib

from app.config import settings


def client_key(request) -> str:
    """Identity to rate-limit on: API key > bearer token > client IP.

    Pure w.r.t. the request headers, so it's unit-testable. Tokens/keys are
    hashed/truncated so raw secrets never become Redis keys.
    """
    api_key = request.headers.get("x-api-key")
    if api_key:
        return f"ak:{hashlib.sha256(api_key.encode()).hexdigest()[:16]}"
    authz = request.headers.get("authorization", "")
    if authz.startswith("Bearer "):
        return f"jwt:{hashlib.sha256(authz[7:].encode()).hexdigest()[:16]}"
    client = getattr(request, "client", None)
    return f"ip:{client.host if client else 'unknown'}"


class RateLimiter:
    def __init__(self) -> None:
        self._redis = None

    def _client(self):
        if self._redis is None:
            import redis.asyncio as aioredis

            self._redis = aioredis.from_url(settings.redis_cache_url)
        return self._redis

    async def allow(self, key: str, limit: int, window_seconds: int = 60) -> bool:
        r = self._client()
        full = f"rl:{key}:{window_seconds}"
        count = await r.incr(full)
        if count == 1:
            await r.expire(full, window_seconds)
        return count <= limit


rate_limiter = RateLimiter()
