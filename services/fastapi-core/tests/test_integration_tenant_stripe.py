"""Integration tests for tenant-owned Stripe revenue sync: credential
connect/config/delete, and the per-tenant webhook."""

import stripe


class _FakeBalance:
    def retrieve(self):
        return {"available": []}


class _FakeStripeClientV1:
    def __init__(self):
        self.balance = _FakeBalance()


class _FakeStripeClient:
    def __init__(self, secret_key):
        self.secret_key = secret_key
        self.v1 = _FakeStripeClientV1()


def _patch_valid_key(monkeypatch):
    monkeypatch.setattr(stripe, "StripeClient", _FakeStripeClient)


async def test_config_reports_unconfigured_by_default(client, tenant_factory):
    acct = await tenant_factory()
    resp = await client.get("/analytics/stripe/config", headers=acct["headers"])
    assert resp.status_code == 200
    assert resp.json() == {
        "configured": False,
        "secret_key_last4": None,
        "display_name": None,
        "webhook_url": None,
    }


async def test_connect_stores_credential_and_validates_key(
    client, tenant_factory, monkeypatch
):
    _patch_valid_key(monkeypatch)
    acct = await tenant_factory()

    resp = await client.post(
        "/analytics/stripe/credentials",
        json={
            "secret_key": "sk_test_abcd1234",
            "webhook_secret": "whsec_test_xyz",
            "display_name": "My SaaS",
        },
        headers=acct["headers"],
    )

    assert resp.status_code == 201
    body = resp.json()
    assert body["configured"] is True
    assert body["secret_key_last4"] == "1234"
    assert body["display_name"] == "My SaaS"
    assert body["webhook_url"].endswith(
        f"/analytics/stripe/webhook/{acct['tenant'].id}"
    )


async def test_connect_rejects_invalid_key(client, tenant_factory, monkeypatch):
    class _RejectingClient:
        def __init__(self, secret_key):
            self.v1 = self

        @property
        def balance(self):
            raise stripe.AuthenticationError("invalid API key")

    monkeypatch.setattr(stripe, "StripeClient", _RejectingClient)
    acct = await tenant_factory()

    resp = await client.post(
        "/analytics/stripe/credentials",
        json={"secret_key": "sk_bad", "webhook_secret": "whsec_x"},
        headers=acct["headers"],
    )
    assert resp.status_code == 400


async def test_connect_rejects_blank_secret_key(client, tenant_factory):
    acct = await tenant_factory()
    resp = await client.post(
        "/analytics/stripe/credentials",
        json={"secret_key": "", "webhook_secret": "whsec_x"},
        headers=acct["headers"],
    )
    assert resp.status_code == 422  # min_length=1 on secret_key


async def test_config_reflects_connected_credential(
    client, tenant_factory, monkeypatch
):
    _patch_valid_key(monkeypatch)
    acct = await tenant_factory()
    await client.post(
        "/analytics/stripe/credentials",
        json={"secret_key": "sk_test_abcd1234", "webhook_secret": "whsec_test_xyz"},
        headers=acct["headers"],
    )

    resp = await client.get("/analytics/stripe/config", headers=acct["headers"])

    assert resp.json()["configured"] is True
    assert resp.json()["secret_key_last4"] == "1234"


async def test_delete_credential(client, tenant_factory, monkeypatch):
    _patch_valid_key(monkeypatch)
    acct = await tenant_factory()
    await client.post(
        "/analytics/stripe/credentials",
        json={"secret_key": "sk_test_abcd1234", "webhook_secret": "whsec_test_xyz"},
        headers=acct["headers"],
    )

    resp = await client.delete("/analytics/stripe/credentials", headers=acct["headers"])
    assert resp.status_code == 204

    after = await client.get("/analytics/stripe/config", headers=acct["headers"])
    assert after.json()["configured"] is False


async def test_stripe_endpoints_require_auth(client):
    assert (await client.get("/analytics/stripe/config")).status_code == 401
    assert (
        await client.post(
            "/analytics/stripe/credentials",
            json={"secret_key": "x", "webhook_secret": "y"},
        )
    ).status_code == 401


# ---- Webhook -----------------------------------------------------------


def _fake_charge_event(event_id="evt_1", charge_id="ch_1", **charge_overrides):
    charge = {
        "id": charge_id,
        "amount_received": 5000,
        "currency": "usd",
        "created": 1_700_000_000,
        "paid": True,
        "metadata": {},
    }
    charge.update(charge_overrides)
    return {"id": event_id, "type": "charge.succeeded", "data": {"object": charge}}


class _FakeStripeEvent(dict):
    def to_dict_recursive(self):
        return dict(self)


async def test_webhook_404_when_not_connected(client):
    import uuid

    resp = await client.post(
        f"/analytics/stripe/webhook/{uuid.uuid4()}",
        content=b"{}",
        headers={"stripe-signature": "t=1,v1=whatever"},
    )
    assert resp.status_code == 404


async def test_webhook_rejects_bad_signature(client, tenant_factory, monkeypatch):
    _patch_valid_key(monkeypatch)
    acct = await tenant_factory()
    await client.post(
        "/analytics/stripe/credentials",
        json={"secret_key": "sk_test_abcd1234", "webhook_secret": "whsec_test_xyz"},
        headers=acct["headers"],
    )

    resp = await client.post(
        f"/analytics/stripe/webhook/{acct['tenant'].id}",
        content=b"{}",
        headers={"stripe-signature": "t=1,v1=deadbeef"},
    )
    assert resp.status_code == 400


async def test_webhook_creates_revenue_event_on_charge_succeeded(
    client, db, tenant_factory, monkeypatch
):
    from sqlalchemy import select

    from app.models.analytics import RevenueEvent

    _patch_valid_key(monkeypatch)
    acct = await tenant_factory()
    await client.post(
        "/analytics/stripe/credentials",
        json={"secret_key": "sk_test_abcd1234", "webhook_secret": "whsec_test_xyz"},
        headers=acct["headers"],
    )

    fake_event = _fake_charge_event()
    monkeypatch.setattr(
        stripe.Webhook,
        "construct_event",
        lambda body, sig, secret: _FakeStripeEvent(fake_event),
    )

    resp = await client.post(
        f"/analytics/stripe/webhook/{acct['tenant'].id}",
        content=b"{}",
        headers={"stripe-signature": "t=1,v1=whatever"},
    )

    assert resp.status_code == 200
    assert resp.json()["status"] == "processed"

    row = await db.execute(
        select(RevenueEvent).where(RevenueEvent.tenant_id == acct["tenant"].id)
    )
    events = row.scalars().all()
    assert len(events) == 1
    assert events[0].amount_cents == 5000
    assert events[0].provider == "stripe"


async def test_webhook_is_idempotent_on_replay(client, db, tenant_factory, monkeypatch):
    from sqlalchemy import select

    from app.models.analytics import RevenueEvent

    _patch_valid_key(monkeypatch)
    acct = await tenant_factory()
    await client.post(
        "/analytics/stripe/credentials",
        json={"secret_key": "sk_test_abcd1234", "webhook_secret": "whsec_test_xyz"},
        headers=acct["headers"],
    )

    fake_event = _fake_charge_event()
    monkeypatch.setattr(
        stripe.Webhook,
        "construct_event",
        lambda body, sig, secret: _FakeStripeEvent(fake_event),
    )

    for _ in range(2):
        resp = await client.post(
            f"/analytics/stripe/webhook/{acct['tenant'].id}",
            content=b"{}",
            headers={"stripe-signature": "t=1,v1=whatever"},
        )
        assert resp.status_code == 200

    row = await db.execute(
        select(RevenueEvent).where(RevenueEvent.tenant_id == acct["tenant"].id)
    )
    assert len(row.scalars().all()) == 1


async def test_webhook_ignores_unpaid_charge(client, db, tenant_factory, monkeypatch):
    from sqlalchemy import select

    from app.models.analytics import RevenueEvent

    _patch_valid_key(monkeypatch)
    acct = await tenant_factory()
    await client.post(
        "/analytics/stripe/credentials",
        json={"secret_key": "sk_test_abcd1234", "webhook_secret": "whsec_test_xyz"},
        headers=acct["headers"],
    )

    fake_event = _fake_charge_event(paid=False)
    monkeypatch.setattr(
        stripe.Webhook,
        "construct_event",
        lambda body, sig, secret: _FakeStripeEvent(fake_event),
    )

    resp = await client.post(
        f"/analytics/stripe/webhook/{acct['tenant'].id}",
        content=b"{}",
        headers={"stripe-signature": "t=1,v1=whatever"},
    )
    assert resp.status_code == 200

    row = await db.execute(
        select(RevenueEvent).where(RevenueEvent.tenant_id == acct["tenant"].id)
    )
    assert row.scalars().all() == []


async def test_webhook_ignores_unhandled_event_types(
    client, db, tenant_factory, monkeypatch
):
    from sqlalchemy import select

    from app.models.analytics import RevenueEvent

    _patch_valid_key(monkeypatch)
    acct = await tenant_factory()
    await client.post(
        "/analytics/stripe/credentials",
        json={"secret_key": "sk_test_abcd1234", "webhook_secret": "whsec_test_xyz"},
        headers=acct["headers"],
    )

    fake_event = {"id": "evt_other", "type": "customer.created", "data": {"object": {}}}
    monkeypatch.setattr(
        stripe.Webhook,
        "construct_event",
        lambda body, sig, secret: _FakeStripeEvent(fake_event),
    )

    resp = await client.post(
        f"/analytics/stripe/webhook/{acct['tenant'].id}",
        content=b"{}",
        headers={"stripe-signature": "t=1,v1=whatever"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "processed"

    row = await db.execute(
        select(RevenueEvent).where(RevenueEvent.tenant_id == acct["tenant"].id)
    )
    assert row.scalars().all() == []


async def test_webhook_events_are_scoped_per_tenant(
    client, db, tenant_factory, monkeypatch
):
    """Two tenants' Stripe accounts could (in principle) emit an event with
    the same id — idempotency must be scoped per tenant, not global."""
    from sqlalchemy import select

    from app.models.analytics import RevenueEvent

    _patch_valid_key(monkeypatch)
    a = await tenant_factory()
    b = await tenant_factory()
    for acct in (a, b):
        await client.post(
            "/analytics/stripe/credentials",
            json={"secret_key": "sk_test_abcd1234", "webhook_secret": "whsec_test_xyz"},
            headers=acct["headers"],
        )

    fake_event = _fake_charge_event(event_id="evt_shared", charge_id="ch_shared")
    monkeypatch.setattr(
        stripe.Webhook,
        "construct_event",
        lambda body, sig, secret: _FakeStripeEvent(fake_event),
    )

    for acct in (a, b):
        resp = await client.post(
            f"/analytics/stripe/webhook/{acct['tenant'].id}",
            content=b"{}",
            headers={"stripe-signature": "t=1,v1=whatever"},
        )
        assert resp.status_code == 200

    row = await db.execute(select(RevenueEvent))
    events = [
        e
        for e in row.scalars().all()
        if e.tenant_id in (a["tenant"].id, b["tenant"].id)
    ]
    assert len(events) == 2
