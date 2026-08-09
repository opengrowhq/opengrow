"""Tests for the rate limiter (off by default; enforced when enabled)."""

from app.config import settings
from app.core.rate_limit import client_key


class _Req:
    def __init__(self, headers=None, ip="1.2.3.4"):
        self.headers = headers or {}
        self.client = type("C", (), {"host": ip})()


def test_client_key_prefers_api_key_then_bearer_then_ip():
    assert client_key(_Req({"x-api-key": "ogk_abc"})).startswith("ak:")
    assert client_key(_Req({"authorization": "Bearer tok"})).startswith("jwt:")
    assert client_key(_Req({}, ip="9.9.9.9")) == "ip:9.9.9.9"


def test_client_key_does_not_leak_the_raw_secret():
    key = client_key(_Req({"x-api-key": "ogk_supersecret"}))
    assert "supersecret" not in key


async def test_disabled_by_default(client, tenant_factory):
    acct = await tenant_factory()
    # Default config → no throttling even under a burst.
    for _ in range(10):
        r = await client.get("/auth/me", headers=acct["headers"])
        assert r.status_code == 200


async def test_enforced_when_enabled(client, tenant_factory, monkeypatch):
    acct = await tenant_factory()
    monkeypatch.setattr(settings, "RATE_LIMIT_ENABLED", True)
    monkeypatch.setattr(settings, "RATE_LIMIT_PER_MINUTE", 3)

    codes = []
    for _ in range(5):
        codes.append(
            (await client.get("/auth/me", headers=acct["headers"])).status_code
        )

    assert codes.count(200) == 3
    assert codes[-1] == 429  # over the limit
