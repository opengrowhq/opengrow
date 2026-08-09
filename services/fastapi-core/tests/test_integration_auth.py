"""Integration tests for the auth flow (real app + DB)."""


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
