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


async def test_topup_requires_auth(client):
    resp = await client.post("/billing/topup", json={"amount_eur_cents": 1000})
    assert resp.status_code == 401


async def test_topup_rejects_amount_outside_fixed_tiers(
    client, tenant_factory, monkeypatch, allow_admin
):
    from app import config

    monkeypatch.setattr(config.settings, "STRIPE_SECRET_KEY", "sk_test_dummy")
    acct = await tenant_factory()
    resp = await client.post(
        "/billing/topup", json={"amount_eur_cents": 999}, headers=acct["headers"]
    )
    assert resp.status_code == 400


async def test_topup_409_on_free_tier(client, tenant_factory, monkeypatch, allow_admin):
    from app import config

    monkeypatch.setattr(config.settings, "STRIPE_SECRET_KEY", "sk_test_dummy")
    acct = await tenant_factory()
    resp = await client.post(
        "/billing/topup", json={"amount_eur_cents": 1000}, headers=acct["headers"]
    )
    assert resp.status_code == 409


async def test_topup_503_when_billing_not_configured(
    client, tenant_factory, monkeypatch, allow_admin
):
    from app import config

    monkeypatch.setattr(config.settings, "STRIPE_SECRET_KEY", "")
    acct = await tenant_factory()
    resp = await client.post(
        "/billing/topup", json={"amount_eur_cents": 1000}, headers=acct["headers"]
    )
    assert resp.status_code == 503


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


def _fake_subscription_event(
    tenant_id: str,
    event_id: str = "evt_sub_1",
    subscription_id: str = "sub_test_1",
) -> dict:
    return {
        "id": event_id,
        "type": "customer.subscription.updated",
        "data": {
            "object": {
                "id": subscription_id,
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
    # First time we see this subscription's period → Pro's monthly grant
    # (1,000 generations * 5c) is credited.
    assert refreshed.credit_balance_cents == 5000


async def test_webhook_does_not_grant_credits_twice_for_the_same_period(
    client, tenant_factory, monkeypatch, db
):
    from app import config
    import stripe
    from sqlalchemy import select
    from app.models.tenant import Tenant

    class _FakeStripeEvent(dict):
        def to_dict_recursive(self):
            return dict(self)

    acct = await tenant_factory()
    tenant_id = str(acct["tenant"].id)
    tenant = await db.get(Tenant, acct["tenant"].id)
    tenant.stripe_customer_id = "cus_test_2"
    await db.commit()

    monkeypatch.setattr(config.settings, "STRIPE_WEBHOOK_SECRET", "whsec_test")
    monkeypatch.setattr(config.settings, "STRIPE_PRICE_ID_PRO", "price_pro_test")

    first_event = _fake_subscription_event(
        tenant_id, event_id="evt_a", subscription_id="sub_test_period_2"
    )
    first_event["data"]["object"]["customer"] = "cus_test_2"
    monkeypatch.setattr(
        stripe.Webhook,
        "construct_event",
        lambda body, sig, secret: _FakeStripeEvent(first_event),
    )
    await client.post(
        "/billing/webhook",
        content=b"{}",
        headers={"stripe-signature": "t=1,v1=whatever"},
    )

    # A second event for the SAME subscription id and SAME period (e.g. an
    # unrelated field update, or a duplicate delivery under a different
    # Stripe event id) must not grant credits again.
    second_event = _fake_subscription_event(
        tenant_id, event_id="evt_b", subscription_id="sub_test_period_2"
    )
    second_event["data"]["object"]["customer"] = "cus_test_2"
    monkeypatch.setattr(
        stripe.Webhook,
        "construct_event",
        lambda body, sig, secret: _FakeStripeEvent(second_event),
    )
    resp = await client.post(
        "/billing/webhook",
        content=b"{}",
        headers={"stripe-signature": "t=1,v1=whatever"},
    )
    assert resp.status_code == 200

    row = await db.execute(
        select(Tenant)
        .where(Tenant.id == acct["tenant"].id)
        .execution_options(populate_existing=True)
    )
    assert row.scalar_one().credit_balance_cents == 5000  # not 10000

    # Re-delivering the same event must be a no-op (idempotency).
    resp2 = await client.post(
        "/billing/webhook",
        content=b"{}",
        headers={"stripe-signature": "t=1,v1=whatever"},
    )
    assert resp2.status_code == 200
    assert resp2.json()["status"] == "already_processed"


def _fake_topup_checkout_event(
    tenant_id: str,
    amount_eur_cents: int,
    event_id: str = "evt_topup_1",
    payment_status: str = "paid",
) -> dict:
    return {
        "id": event_id,
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "id": "cs_test_topup_1",
                "payment_status": payment_status,
                "metadata": {
                    "opengrow_tenant_id": tenant_id,
                    "opengrow_kind": "credit_topup",
                    "opengrow_amount_eur_cents": str(amount_eur_cents),
                },
            }
        },
    }


class _FakeStripeEvent(dict):
    def to_dict_recursive(self):
        return dict(self)


async def test_webhook_topup_grants_credit_with_markup_applied(
    client, tenant_factory, monkeypatch, db
):
    from app import config
    import stripe
    from sqlalchemy import select
    from app.models.tenant import Tenant

    acct = await tenant_factory()
    tenant = await db.get(Tenant, acct["tenant"].id)
    tenant.billing_plan = "pro"
    await db.commit()

    monkeypatch.setattr(config.settings, "STRIPE_WEBHOOK_SECRET", "whsec_test")
    fake_event = _fake_topup_checkout_event(str(acct["tenant"].id), 2_500)
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

    row = await db.execute(
        select(Tenant)
        .where(Tenant.id == acct["tenant"].id)
        .execution_options(populate_existing=True)
    )
    # €25 (2500c) paid, 25% markup → 75% passed through as credit: 1875c.
    assert row.scalar_one().credit_balance_cents == 1875


async def test_webhook_topup_does_not_grant_credit_when_unpaid(
    client, tenant_factory, monkeypatch, db
):
    """A Checkout Session can complete without payment_status=paid in some
    Stripe flows (e.g. deferred payment methods) — must never grant credit
    for a session that hasn't actually been paid."""
    from app import config
    import stripe
    from sqlalchemy import select
    from app.models.tenant import Tenant

    acct = await tenant_factory()
    tenant = await db.get(Tenant, acct["tenant"].id)
    tenant.billing_plan = "pro"
    await db.commit()

    monkeypatch.setattr(config.settings, "STRIPE_WEBHOOK_SECRET", "whsec_test")
    fake_event = _fake_topup_checkout_event(
        str(acct["tenant"].id), 2_500, payment_status="unpaid"
    )
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

    row = await db.execute(
        select(Tenant)
        .where(Tenant.id == acct["tenant"].id)
        .execution_options(populate_existing=True)
    )
    assert row.scalar_one().credit_balance_cents == 0


async def test_webhook_topup_does_not_change_billing_plan(
    client, tenant_factory, monkeypatch, db
):
    """A top-up session must only grant credit, never touch billing_plan —
    that's the subscription Checkout session's job (opengrow_plan metadata),
    which a top-up session doesn't carry."""
    from app import config
    import stripe
    from sqlalchemy import select
    from app.models.tenant import Tenant

    acct = await tenant_factory()
    tenant = await db.get(Tenant, acct["tenant"].id)
    tenant.billing_plan = "team"
    await db.commit()

    monkeypatch.setattr(config.settings, "STRIPE_WEBHOOK_SECRET", "whsec_test")
    fake_event = _fake_topup_checkout_event(str(acct["tenant"].id), 1_000)
    monkeypatch.setattr(
        stripe.Webhook,
        "construct_event",
        lambda body, sig, secret: _FakeStripeEvent(fake_event),
    )

    await client.post(
        "/billing/webhook",
        content=b"{}",
        headers={"stripe-signature": "t=1,v1=whatever"},
    )

    row = await db.execute(
        select(Tenant)
        .where(Tenant.id == acct["tenant"].id)
        .execution_options(populate_existing=True)
    )
    assert row.scalar_one().billing_plan == "team"
