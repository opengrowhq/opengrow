"""Integration tests for the Google connector OAuth state hardening."""

import pytest

from app.config import settings
from app.core.oauth_state import consume_oauth_state, issue_oauth_state


@pytest.fixture
def google_oauth_settings(monkeypatch):
    monkeypatch.setattr(settings, "GOOGLE_OAUTH_CLIENT_ID", "cid")
    monkeypatch.setattr(settings, "GOOGLE_OAUTH_CLIENT_SECRET", "secret")
    monkeypatch.setattr(
        settings, "GOOGLE_OAUTH_REDIRECT_URI", "https://app.test/oauth/callback"
    )
    return settings


@pytest.fixture
def fake_token_exchange(monkeypatch):
    async def fake(**kwargs):
        return {
            "access_token": "ya29.fake",
            "refresh_token": "refresh.fake",
            "expires_in": 3600,
            "token_type": "Bearer",
            "scope": "scope",
        }

    monkeypatch.setattr("app.routers.analytics.exchange_google_oauth_code", fake)
    return fake


async def _create_connector(client, headers, provider="ga4"):
    resp = await client.post(
        "/analytics/connectors",
        json={"provider": provider, "display_name": "GA", "external_property_id": "1"},
        headers=headers,
    )
    assert resp.status_code in (200, 201)
    return resp.json()["id"]


async def _auth_url_state(client, headers, provider="ga4"):
    resp = await client.get(
        f"/analytics/connectors/google/auth-url?provider={provider}", headers=headers
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["configured"] is True
    assert body["state"]
    return body["state"]


async def test_auth_url_issues_consumable_state(
    client, tenant_factory, google_oauth_settings
):
    acct = await tenant_factory()
    state = await _auth_url_state(client, acct["headers"])
    stored = await consume_oauth_state(state)
    assert stored is not None
    assert stored["provider"] == "ga4"
    assert stored["tenant_id"] == str(acct["tenant"].id)
    # Single-use: a second consume finds nothing.
    assert await consume_oauth_state(state) is None


async def test_callback_rejects_missing_or_invalid_state(
    client, tenant_factory, google_oauth_settings, fake_token_exchange
):
    acct = await tenant_factory()
    h = acct["headers"]
    cid = await _create_connector(client, h)

    missing = await client.post(
        f"/analytics/connectors/{cid}/google/callback",
        json={"code": "abc"},
        headers=h,
    )
    assert missing.status_code == 422

    invalid = await client.post(
        f"/analytics/connectors/{cid}/google/callback",
        json={"code": "abc", "state": "never-issued"},
        headers=h,
    )
    assert invalid.status_code == 400


async def test_callback_rejects_other_tenants_state(
    client, tenant_factory, google_oauth_settings, fake_token_exchange
):
    a = await tenant_factory()
    b = await tenant_factory()
    cid = await _create_connector(client, b["headers"])
    state_b = await _auth_url_state(client, b["headers"])
    foreign_state = await issue_oauth_state(
        provider="ga4", tenant_id=str(a["tenant"].id), user_id="someone"
    )

    resp = await client.post(
        f"/analytics/connectors/{cid}/google/callback",
        json={"code": "abc", "state": foreign_state},
        headers=b["headers"],
    )
    assert resp.status_code == 403
    # The issued-but-unused state for tenant b is untouched.
    assert await consume_oauth_state(state_b) is not None


async def test_callback_rejects_provider_mismatch(
    client, tenant_factory, google_oauth_settings, fake_token_exchange
):
    acct = await tenant_factory()
    h = acct["headers"]
    cid = await _create_connector(client, h, provider="ga4")
    state = await _auth_url_state(client, h, provider="gsc")

    resp = await client.post(
        f"/analytics/connectors/{cid}/google/callback",
        json={"code": "abc", "state": state},
        headers=h,
    )
    assert resp.status_code == 400


async def test_callback_happy_path_connects(
    client, tenant_factory, google_oauth_settings, fake_token_exchange
):
    acct = await tenant_factory()
    h = acct["headers"]
    cid = await _create_connector(client, h)
    state = await _auth_url_state(client, h)

    resp = await client.post(
        f"/analytics/connectors/{cid}/google/callback",
        json={"code": "abc", "state": state},
        headers=h,
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "CONNECTED"

    # Replay with the same (now consumed) state fails.
    replay = await client.post(
        f"/analytics/connectors/{cid}/google/callback",
        json={"code": "abc", "state": state},
        headers=h,
    )
    assert replay.status_code == 400
