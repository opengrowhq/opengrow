"""Integration tests for API keys (create → use as X-API-Key → revoke)."""


async def test_create_key_then_authenticate_with_it(client, tenant_factory):
    acct = await tenant_factory()
    h = acct["headers"]

    created = await client.post("/api-keys", json={"name": "ci"}, headers=h)
    assert created.status_code == 201
    body = created.json()
    assert body["key"].startswith("ogk_")
    assert body["prefix"] == body["key"][:12]
    assert body["name"] == "ci"

    # The plaintext key authenticates like a Bearer token, no JWT needed.
    me = await client.get("/auth/me", headers={"X-API-Key": body["key"]})
    assert me.status_code == 200
    assert me.json()["tenant_slug"] == acct["tenant"].slug

    # And it works on a normal resource endpoint.
    content = await client.post(
        "/content", json={"title": "via key"}, headers={"X-API-Key": body["key"]}
    )
    assert content.status_code == 201


async def test_list_never_returns_plaintext(client, tenant_factory):
    acct = await tenant_factory()
    h = acct["headers"]
    await client.post("/api-keys", json={"name": "one"}, headers=h)

    listing = await client.get("/api-keys", headers=h)
    assert listing.status_code == 200
    assert len(listing.json()) == 1
    assert "key" not in listing.json()[0]  # only prefix is exposed
    assert listing.json()[0]["prefix"].startswith("ogk_")


async def test_revoked_key_stops_working(client, tenant_factory):
    acct = await tenant_factory()
    h = acct["headers"]
    created = (await client.post("/api-keys", json={}, headers=h)).json()
    key_id, raw = created["id"], created["key"]

    assert (await client.get("/auth/me", headers={"X-API-Key": raw})).status_code == 200

    revoked = await client.delete(f"/api-keys/{key_id}", headers=h)
    assert revoked.status_code == 204

    assert (await client.get("/auth/me", headers={"X-API-Key": raw})).status_code == 401
    # revoked key no longer appears in the list
    assert (await client.get("/api-keys", headers=h)).json() == []


async def test_bad_key_is_rejected(client):
    resp = await client.get("/auth/me", headers={"X-API-Key": "ogk_not-a-real-key"})
    assert resp.status_code == 401


async def test_keys_are_tenant_scoped(client, tenant_factory):
    a = await tenant_factory()
    b = await tenant_factory()
    a_key_id = (await client.post("/api-keys", json={}, headers=a["headers"])).json()[
        "id"
    ]

    # B cannot revoke A's key.
    resp = await client.delete(f"/api-keys/{a_key_id}", headers=b["headers"])
    assert resp.status_code == 404
