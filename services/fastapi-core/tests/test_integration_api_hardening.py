"""Integration tests for Scope A: pagination, error envelope, /version."""

from app.version import API_VERSION


async def test_version_endpoint(client):
    resp = await client.get("/version")
    assert resp.status_code == 200
    body = resp.json()
    assert body["version"] == API_VERSION
    assert body["service"]
    assert body["mode"] in ("lite", "production")


async def test_content_pagination_and_total_header(client, tenant_factory):
    acct = await tenant_factory()
    h = acct["headers"]
    for i in range(5):
        await client.post("/content", json={"title": f"post {i}"}, headers=h)

    # No params → full list + X-Total-Count header (non-breaking).
    full = await client.get("/content", headers=h)
    assert full.status_code == 200
    assert len(full.json()) == 5
    assert full.headers["X-Total-Count"] == "5"

    # limit/offset slice the array; header still reports the full total.
    page = await client.get("/content?limit=2&offset=1", headers=h)
    assert len(page.json()) == 2
    assert page.headers["X-Total-Count"] == "5"


async def test_pagination_is_tenant_scoped_total(client, tenant_factory):
    a = await tenant_factory()
    b = await tenant_factory()
    for i in range(3):
        await client.post("/content", json={"title": f"a{i}"}, headers=a["headers"])

    resp_b = await client.get("/content", headers=b["headers"])
    assert resp_b.headers["X-Total-Count"] == "0"


async def test_validation_error_detail_is_a_string(client, tenant_factory):
    acct = await tenant_factory()
    # Missing required "title" → 422 with a readable string detail (+ errors list).
    resp = await client.post("/content", json={}, headers=acct["headers"])
    assert resp.status_code == 422
    body = resp.json()
    assert isinstance(body["detail"], str)
    assert "title" in body["detail"]
    assert isinstance(body["errors"], list)


async def test_bad_limit_rejected(client, tenant_factory):
    acct = await tenant_factory()
    resp = await client.get("/content?limit=9999", headers=acct["headers"])
    assert resp.status_code == 422  # over MAX_LIMIT
