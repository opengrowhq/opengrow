from __future__ import annotations

from urllib.parse import urlencode

import httpx


GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_SCOPES = {
    "ga4": ["https://www.googleapis.com/auth/analytics.readonly"],
    "gsc": ["https://www.googleapis.com/auth/webmasters.readonly"],
}


def google_scopes(provider: str) -> list[str]:
    return GOOGLE_SCOPES.get(provider, [])


def build_google_auth_url(
    *,
    client_id: str,
    redirect_uri: str,
    provider: str,
    state: str,
) -> str:
    scopes = google_scopes(provider)
    query = urlencode(
        {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": " ".join(scopes),
            "access_type": "offline",
            "prompt": "consent",
            "state": state,
        }
    )
    return f"{GOOGLE_AUTH_URL}?{query}"


def google_token_payload(
    *,
    client_id: str,
    client_secret: str,
    redirect_uri: str,
    code: str,
) -> dict[str, str]:
    return {
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": redirect_uri,
        "code": code,
        "grant_type": "authorization_code",
    }


def google_refresh_payload(
    *,
    client_id: str,
    client_secret: str,
    refresh_token: str,
) -> dict[str, str]:
    return {
        "client_id": client_id,
        "client_secret": client_secret,
        "refresh_token": refresh_token,
        "grant_type": "refresh_token",
    }


class GoogleOAuthError(Exception):
    pass


async def exchange_google_oauth_code(
    *,
    client_id: str,
    client_secret: str,
    redirect_uri: str,
    code: str,
) -> dict:
    async with httpx.AsyncClient(timeout=15, trust_env=False) as client:
        response = await client.post(
            GOOGLE_TOKEN_URL,
            data=google_token_payload(
                client_id=client_id,
                client_secret=client_secret,
                redirect_uri=redirect_uri,
                code=code,
            ),
            headers={"Accept": "application/json"},
        )
    if response.status_code >= 400:
        raise GoogleOAuthError("Google OAuth token exchange failed")
    data = response.json()
    if not data.get("access_token"):
        raise GoogleOAuthError(
            "Google OAuth token response did not include access_token"
        )
    return data


async def refresh_google_access_token(
    *,
    client_id: str,
    client_secret: str,
    refresh_token: str,
) -> dict:
    async with httpx.AsyncClient(timeout=15, trust_env=False) as client:
        response = await client.post(
            GOOGLE_TOKEN_URL,
            data=google_refresh_payload(
                client_id=client_id,
                client_secret=client_secret,
                refresh_token=refresh_token,
            ),
            headers={"Accept": "application/json"},
        )
    if response.status_code >= 400:
        raise GoogleOAuthError("Google OAuth refresh failed")
    data = response.json()
    if not data.get("access_token"):
        raise GoogleOAuthError(
            "Google OAuth refresh response did not include access_token"
        )
    return data
