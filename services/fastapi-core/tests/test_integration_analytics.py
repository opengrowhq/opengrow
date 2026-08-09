"""Integration tests for analytics events → attribution summary + tracking."""


async def test_events_roll_up_into_summary(client, tenant_factory):
    acct = await tenant_factory()
    h = acct["headers"]

    # Two visits and one revenue event.
    for _ in range(2):
        r = await client.post(
            "/analytics/events", json={"event_type": "VISIT"}, headers=h
        )
        assert r.status_code == 201
    rev = await client.post(
        "/analytics/events",
        json={"event_type": "REVENUE", "amount_cents": 34000, "currency": "USD"},
        headers=h,
    )
    assert rev.status_code == 201

    summary = await client.get("/analytics/summary", headers=h)
    assert summary.status_code == 200
    body = summary.json()
    assert body["visits"] == 2
    assert body["revenue_cents"] == 34000
    assert body["events"] >= 3


async def test_summary_is_tenant_scoped(client, tenant_factory):
    a = await tenant_factory()
    b = await tenant_factory()
    await client.post(
        "/analytics/events", json={"event_type": "LEAD"}, headers=a["headers"]
    )

    # Tenant B sees none of tenant A's events.
    summary_b = await client.get("/analytics/summary", headers=b["headers"])
    assert summary_b.json()["leads"] == 0


async def test_public_pixel_and_tracking_status(client, tenant_factory):
    acct = await tenant_factory()
    slug = acct["tenant"].slug

    # Public pixel (no auth) records a first-party visit and returns a GIF.
    pixel = await client.get(f"/analytics/pixel.gif?tenant={slug}")
    assert pixel.status_code == 200
    assert pixel.headers["content-type"].startswith("image/gif")

    status = await client.get("/analytics/tracking/status", headers=acct["headers"])
    assert status.status_code == 200
    assert status.json()["installed"] is True


async def test_events_require_auth(client):
    resp = await client.post("/analytics/events", json={"event_type": "VISIT"})
    assert resp.status_code == 401
