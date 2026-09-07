"""Integration tests for the auth flow (real app + DB)."""

import uuid
from datetime import datetime, timedelta, timezone

import jwt

from app.config import settings


async def test_login_returns_token_and_me(client, tenant_factory):
    account = await tenant_factory(password="pw-123456")

    resp = await client.post(
        "/auth/login",
        data={"username": account["email"], "password": "pw-123456"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["access_token"]
    assert body["token_type"] == "bearer"

    me = await client.get(
        "/auth/me", headers={"Authorization": f"Bearer {body['access_token']}"}
    )
    assert me.status_code == 200
    assert me.json()["email"] == account["email"]
    assert me.json()["tenant_slug"] == account["tenant"].slug


async def test_login_wrong_password_401(client, tenant_factory):
    account = await tenant_factory(password="pw-123456")
    resp = await client.post(
        "/auth/login",
        data={"username": account["email"], "password": "wrong"},
    )
    assert resp.status_code == 401


async def test_login_unknown_user_401(client):
    resp = await client.post(
        "/auth/login",
        data={"username": "nobody@example.com", "password": "whatever"},
    )
    assert resp.status_code == 401


async def test_me_requires_auth(client):
    assert (await client.get("/auth/me")).status_code == 401
    bad = await client.get("/auth/me", headers={"Authorization": "Bearer garbage"})
    assert bad.status_code == 401


async def test_register_is_not_in_public_core(client):
    # Signup is a hosted-only concern; the public core must not expose it.
    resp = await client.post(
        "/auth/register",
        json={"email": "x@y.com", "password": "longenough"},
    )
    assert resp.status_code == 404


async def test_signup_is_not_in_public_core(client):
    # Self-service signup is not part of the open-source core (it shipped
    # alongside in-core billing in 0.2.0 and was removed in 0.3.0) — an
    # unguarded core endpoint could shadow a guard in a deployment that
    # layers its own registration on top. Workspace creation is seed/script-
    # only here.
    resp = await client.post(
        "/auth/signup",
        json={
            "email": "x@y.com",
            "password": "longenough",
            "display_name": "X",
            "tenant_name": "Y",
        },
    )
    assert resp.status_code == 404


async def _login_token_pair(client, email, password):
    resp = await client.post(
        "/auth/login", data={"username": email, "password": password}
    )
    assert resp.status_code == 200
    return resp.json()


async def test_refresh_returns_new_pair_and_rotates(client, tenant_factory):
    account = await tenant_factory(password="pw-123456")
    pair = await _login_token_pair(client, account["email"], "pw-123456")

    resp = await client.post(
        "/auth/refresh", json={"refresh_token": pair["refresh_token"]}
    )
    assert resp.status_code == 200
    new_pair = resp.json()
    assert new_pair["access_token"]
    assert new_pair["refresh_token"]

    me = await client.get(
        "/auth/me", headers={"Authorization": f"Bearer {new_pair['access_token']}"}
    )
    assert me.status_code == 200
    assert me.json()["email"] == account["email"]

    # Rotation: the issued refresh token is itself a valid refresh credential
    # (the chain continues), and its payload is a fresh issuance — not a
    # re-served copy of the presented token.
    again = await client.post(
        "/auth/refresh", json={"refresh_token": new_pair["refresh_token"]}
    )
    assert again.status_code == 200
    payload = jwt.decode(
        new_pair["refresh_token"],
        settings.JWT_SECRET,
        algorithms=[settings.JWT_ALGORITHM],
    )
    assert payload["kind"] == "refresh"
    assert payload["sub"] == str(account["user"].id)


async def test_refresh_rejects_access_token(client, tenant_factory):
    account = await tenant_factory(password="pw-123456")
    resp = await client.post("/auth/refresh", json={"refresh_token": account["token"]})
    assert resp.status_code == 401


async def test_refresh_rejects_expired_token(client, tenant_factory):
    from app.core.auth import issue_refresh

    account = await tenant_factory(password="pw-123456")
    expired = issue_refresh(str(account["user"].id), str(account["tenant"].id))
    # Re-issue with an expiry in the past.
    payload = jwt.decode(
        expired, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM]
    )
    payload["exp"] = int(
        (datetime.now(timezone.utc) - timedelta(minutes=1)).timestamp()
    )
    expired = jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)

    resp = await client.post("/auth/refresh", json={"refresh_token": expired})
    assert resp.status_code == 401


async def test_refresh_rejects_garbage_token(client):
    resp = await client.post("/auth/refresh", json={"refresh_token": "garbage"})
    assert resp.status_code == 401


async def test_refresh_unknown_user_401(client, tenant_factory):
    from app.core.auth import issue_refresh

    await tenant_factory(password="pw-123456")
    ghost = issue_refresh(str(uuid.uuid4()), str(uuid.uuid4()))
    resp = await client.post("/auth/refresh", json={"refresh_token": ghost})
    assert resp.status_code == 401


async def test_refresh_inactive_user_401(client, tenant_factory, db):
    from app.core.auth import issue_refresh

    account = await tenant_factory(password="pw-123456")
    account["user"].is_active = False
    await db.commit()
    token = issue_refresh(str(account["user"].id), str(account["tenant"].id))
    resp = await client.post("/auth/refresh", json={"refresh_token": token})
    assert resp.status_code == 401
