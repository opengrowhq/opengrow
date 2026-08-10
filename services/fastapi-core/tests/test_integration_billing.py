"""Integration tests for the billing router (Checkout/Portal/webhook)."""

import pytest


@pytest.fixture
def allow_admin(monkeypatch):
    """Stub authz to allow tenant-admin checks — this repo's local dev
    environment has no OpenFGA store configured, so authz.check() always
    fails closed here regardless of the real permission logic being tested."""
    from app.core import authz

    async def _allow(user_id: str, relation: str, object_id: str) -> bool:
        return True

    monkeypatch.setattr(authz.authz_client, "check", _allow)


async def test_checkout_requires_auth(client):
    resp = await client.post("/billing/checkout", json={"plan": "pro"})
    assert resp.status_code == 401


async def test_portal_requires_auth(client):
    resp = await client.post("/billing/portal")
    assert resp.status_code == 401


async def test_subscription_requires_auth(client):
    resp = await client.get("/billing/subscription")
    assert resp.status_code == 401


async def test_checkout_rejects_unknown_plan(client, tenant_factory, monkeypatch, allow_admin):
    from app import config

    monkeypatch.setattr(config.settings, "STRIPE_SECRET_KEY", "sk_test_dummy")
    acct = await tenant_factory()
    resp = await client.post(
        "/billing/checkout", json={"plan": "enterprise"}, headers=acct["headers"]
    )
    assert resp.status_code == 400


async def test_checkout_503_when_billing_not_configured(
    client, tenant_factory, monkeypatch, allow_admin
):
    from app import config

    monkeypatch.setattr(config.settings, "STRIPE_SECRET_KEY", "")
    acct = await tenant_factory()
    resp = await client.post(
        "/billing/checkout", json={"plan": "pro"}, headers=acct["headers"]
    )
    assert resp.status_code == 503


async def test_subscription_defaults_to_free_plan(client, tenant_factory):
    acct = await tenant_factory()
    resp = await client.get("/billing/subscription", headers=acct["headers"])
    assert resp.status_code == 200
    body = resp.json()
    assert body["billing_plan"] == "free"
    assert body["subscription_status"] is None


async def test_portal_409_without_stripe_customer(
    client, tenant_factory, monkeypatch, allow_admin
):
    from app import config

    monkeypatch.setattr(config.settings, "STRIPE_SECRET_KEY", "sk_test_dummy")
    acct = await tenant_factory()
    resp = await client.post("/billing/portal", headers=acct["headers"])
    assert resp.status_code == 409


async def test_webhook_503_when_not_configured(client):
    resp = await client.post(
        "/billing/webhook",
        content=b"{}",
        headers={"stripe-signature": "t=1,v1=deadbeef"},
    )
    assert resp.status_code == 503


async def test_webhook_rejects_bad_signature(client, monkeypatch):
    from app import config

    monkeypatch.setattr(config.settings, "STRIPE_WEBHOOK_SECRET", "whsec_test")
    resp = await client.post(
        "/billing/webhook",
        content=b'{"id": "evt_1", "type": "checkout.session.completed"}',
        headers={"stripe-signature": "t=1,v1=deadbeef"},
    )
    assert resp.status_code == 400


def _fake_subscription_event(tenant_id: str, event_id: str = "evt_sub_1") -> dict:
    return {
        "id": event_id,
        "type": "customer.subscription.updated",
        "data": {
            "object": {
                "id": "sub_test_1",
                "customer": "cus_test_1",
                "status": "active",
                "cancel_at_period_end": False,
                "items": {
                    "data": [
                        {
                            "price": {"id": "price_pro_test"},
                            "current_period_start": 1_700_000_000,
                            "current_period_end": 1_702_592_000,
                        }
                    ]
                },
            }
        },
    }


async def test_webhook_subscription_updated_persists_and_activates_plan(
    client, tenant_factory, monkeypatch, db
):
    from app import config
    import stripe
    from sqlalchemy import select
    from app.models.tenant import Tenant
    from app.models.subscription import Subscription

    acct = await tenant_factory()
    tenant_id = str(acct["tenant"].id)

    tenant = await db.get(Tenant, acct["tenant"].id)
    tenant.stripe_customer_id = "cus_test_1"
    await db.commit()

    monkeypatch.setattr(config.settings, "STRIPE_WEBHOOK_SECRET", "whsec_test")
    monkeypatch.setattr(config.settings, "STRIPE_PRICE_ID_PRO", "price_pro_test")
    fake_event = _fake_subscription_event(tenant_id)

    class _FakeStripeEvent(dict):
        def to_dict_recursive(self):
            return dict(self)

    monkeypatch.setattr(
        stripe.Webhook,
        "construct_event",
        lambda body, sig, secret: _FakeStripeEvent(fake_event),
    )

    resp = await client.post(
        "/billing/webhook",
        content=b"{}",
        headers={"stripe-signature": "t=1,v1=whatever"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "processed"

    row = await db.execute(
        select(Subscription).where(Subscription.tenant_id == acct["tenant"].id)
    )
    sub = row.scalar_one()
    assert sub.plan == "pro"
    assert sub.status.value == "ACTIVE"

    # Separate session than the one the webhook request used underneath —
    # this session's identity map still holds the pre-webhook `tenant`
    # object (expire_on_commit=False), so force a re-fetch from the DB
    # instead of serving that stale cached instance.
    row = await db.execute(
        select(Tenant)
        .where(Tenant.id == acct["tenant"].id)
        .execution_options(populate_existing=True)
    )
    refreshed = row.scalar_one()
    assert refreshed.billing_plan == "pro"

    # Re-delivering the same event must be a no-op (idempotency).
    resp2 = await client.post(
        "/billing/webhook",
        content=b"{}",
        headers={"stripe-signature": "t=1,v1=whatever"},
    )
    assert resp2.status_code == 200
    assert resp2.json()["status"] == "already_processed"
