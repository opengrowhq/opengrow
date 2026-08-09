from urllib.parse import parse_qs, urlparse

from app.core.google_oauth import (
    build_google_auth_url,
    google_scopes,
    google_refresh_payload,
    google_token_payload,
)


def test_google_scopes_are_provider_specific():
    assert google_scopes("ga4") == [
        "https://www.googleapis.com/auth/analytics.readonly"
    ]
    assert google_scopes("gsc") == [
        "https://www.googleapis.com/auth/webmasters.readonly"
    ]


def test_build_google_auth_url_uses_offline_code_flow():
    url = build_google_auth_url(
        client_id="client-id",
        redirect_uri="https://app.example.test/oauth/google/callback",
        provider="gsc",
        state="state-token",
    )
    parsed = urlparse(url)
    query = parse_qs(parsed.query)

    assert parsed.netloc == "accounts.google.com"
    assert query["client_id"] == ["client-id"]
    assert query["response_type"] == ["code"]
    assert query["access_type"] == ["offline"]
    assert query["prompt"] == ["consent"]
    assert query["scope"] == ["https://www.googleapis.com/auth/webmasters.readonly"]
    assert query["state"] == ["state-token"]


def test_google_token_payload_uses_authorization_code_grant():
    assert google_token_payload(
        client_id="client-id",
        client_secret="client-secret",
        redirect_uri="https://app.example.test/oauth/google/callback",
        code="code",
    ) == {
        "client_id": "client-id",
        "client_secret": "client-secret",
        "redirect_uri": "https://app.example.test/oauth/google/callback",
        "code": "code",
        "grant_type": "authorization_code",
    }


def test_google_refresh_payload_uses_refresh_token_grant():
    assert google_refresh_payload(
        client_id="client-id",
        client_secret="client-secret",
        refresh_token="refresh-token",
    ) == {
        "client_id": "client-id",
        "client_secret": "client-secret",
        "refresh_token": "refresh-token",
        "grant_type": "refresh_token",
    }
