"""Integration tests for seat-based Team pricing: sync_seat_quantity's
Stripe-item math, and its wiring into invite-accept + member removal."""

import uuid
from datetime import datetime, timedelta, timezone

import pytest

from app.config import settings

# _StubAuthZClient.check() (app/core/authz.py) always returns True under
# DEPLOYMENT_MODE=lite by design — there's no real OpenFGA to deny against.
# A test relying on an unstubbed authz_client.check() denying a non-admin
# can't see that denial in lite mode, including in CI (ci.yml runs
# DEPLOYMENT_MODE: lite).
requires_real_authz = pytest.mark.skipif(
    settings.is_lite,
    reason="authz_client.check() always allows under DEPLOYMENT_MODE=lite",
)


@pytest.fixture
def allow_admin(monkeypatch):
    from app.core import authz

    async def _allow(user_id: str, relation: str, object_id: str) -> bool:
        return True

    async def _noop(user_id, tenant_id, role="member"):
        return None

    monkeypatch.setattr(authz.authz_client, "check", _allow)
    monkeypatch.setattr(authz.authz_client, "write_membership", _noop)


@pytest.fixture
def no_smtp(monkeypatch):
    from app.routers import invites

    monkeypatch.setattr(invites, "_send_invite_email", lambda *a, **k: None)


def _admin_only_for(admin_user_id: str):
    """authz.check() stub distinguishing a specific user as the tenant's
    only admin — everyone else reads as a non-admin member. Lets a test
    exercise both "caller must be admin" (passes) and "target is/isn't an
    admin" (varies) against real per-user identity, unlike a blanket
    allow-everything stub."""

    async def _check(user_id: str, relation: str, object_id: str) -> bool:
        if relation == "admin":
            return user_id == admin_user_id
        return True  # member/reader/writer checks unrelated to this test

    return _check


class _FakeSubscriptionItems:
    def __init__(self):
        self.created = []
        self.updated = []
        self.deleted = []
        self._next_id = 0

    def create(self, params):
        self._next_id += 1
        item_id = f"si_new_{self._next_id}"
        self.created.append(params)
        return type("Item", (), {"id": item_id})()

    def update(self, item_id, params):
        self.updated.append((item_id, params))

    def delete(self, item_id):
        self.deleted.append(item_id)


class _FakeStripeClient:
    def __init__(self):
        self.v1 = type("V1", (), {"subscription_items": _FakeSubscriptionItems()})()


@pytest.fixture
def fake_stripe_client(monkeypatch):
    from app import config
    from app.routers import billing

    monkeypatch.setattr(config.settings, "STRIPE_SECRET_KEY", "sk_test_dummy")
    monkeypatch.setattr(config.settings, "STRIPE_PRICE_ID_TEAM_SEAT", "price_seat_test")
    monkeypatch.setattr(config.settings, "TEAM_INCLUDED_SEATS", 5)
    fake = _FakeStripeClient()
    monkeypatch.setattr(billing, "_client", lambda: fake)
    return fake


async def _make_team_tenant_with_subscription(db, extra_seats=0, seat_item_id=None):
    from app.models.tenant import Tenant
    from app.models.subscription import Subscription, SubscriptionStatus

    suffix = uuid.uuid4().hex[:10]
    tenant = Tenant(
        id=uuid.uuid4(),
        slug=f"t-{suffix}",
        name=f"Tenant {suffix}",
        billing_plan="team",
        stripe_customer_id=f"cus_{suffix}",
    )
    db.add(tenant)
    await db.commit()

    now = datetime.now(timezone.utc)
    sub = Subscription(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        stripe_subscription_id=f"sub_{suffix}",
        stripe_price_id="price_team_test",
        plan="team",
        status=SubscriptionStatus.ACTIVE,
        current_period_start=now,
        current_period_end=now + timedelta(days=30),
        extra_seats=extra_seats,
        stripe_seat_item_id=seat_item_id,
    )
    db.add(sub)
    await db.commit()
    return tenant, sub


async def test_sync_seat_quantity_creates_seat_item_when_first_needed(
    db, fake_stripe_client
):
    from app.routers.billing import sync_seat_quantity
    from sqlalchemy import select
    from app.models.subscription import Subscription

    tenant, sub = await _make_team_tenant_with_subscription(db, extra_seats=0)

    # 5 included + 2 extra = 7 total members.
    await sync_seat_quantity(db, tenant.id, member_count=7)

    assert len(fake_stripe_client.v1.subscription_items.created) == 1
    created = fake_stripe_client.v1.subscription_items.created[0]
    assert created["quantity"] == 2
    assert created["price"] == "price_seat_test"

    refreshed = await db.scalar(
        select(Subscription)
        .where(Subscription.id == sub.id)
        .execution_options(populate_existing=True)
    )
    assert refreshed.extra_seats == 2
    assert refreshed.stripe_seat_item_id == "si_new_1"


async def test_sync_seat_quantity_updates_existing_seat_item(db, fake_stripe_client):
    from app.routers.billing import sync_seat_quantity
    from sqlalchemy import select
    from app.models.subscription import Subscription

    tenant, sub = await _make_team_tenant_with_subscription(
        db, extra_seats=2, seat_item_id="si_existing"
    )

    # Grew from 7 to 9 members (5 included + 4 extra).
    await sync_seat_quantity(db, tenant.id, member_count=9)

    assert fake_stripe_client.v1.subscription_items.updated == [
        ("si_existing", {"quantity": 4})
    ]
    refreshed = await db.scalar(
        select(Subscription)
        .where(Subscription.id == sub.id)
        .execution_options(populate_existing=True)
    )
    assert refreshed.extra_seats == 4


async def test_sync_seat_quantity_removes_seat_item_when_back_to_included(
    db, fake_stripe_client
):
    from app.routers.billing import sync_seat_quantity
    from sqlalchemy import select
    from app.models.subscription import Subscription

    tenant, sub = await _make_team_tenant_with_subscription(
        db, extra_seats=2, seat_item_id="si_existing"
    )

    # Shrank back to exactly the included 5 seats.
    await sync_seat_quantity(db, tenant.id, member_count=5)

    assert fake_stripe_client.v1.subscription_items.deleted == ["si_existing"]
    refreshed = await db.scalar(
        select(Subscription)
        .where(Subscription.id == sub.id)
        .execution_options(populate_existing=True)
    )
    assert refreshed.extra_seats == 0
    assert refreshed.stripe_seat_item_id is None


async def test_sync_seat_quantity_is_a_noop_when_already_in_sync(db, fake_stripe_client):
    from app.routers.billing import sync_seat_quantity

    tenant, sub = await _make_team_tenant_with_subscription(
        db, extra_seats=2, seat_item_id="si_existing"
    )

    await sync_seat_quantity(db, tenant.id, member_count=7)  # already 2 extra seats

    assert fake_stripe_client.v1.subscription_items.updated == []
    assert fake_stripe_client.v1.subscription_items.created == []
    assert fake_stripe_client.v1.subscription_items.deleted == []


async def test_sync_seat_quantity_noop_for_non_team_tenant(db, fake_stripe_client):
    from app.routers.billing import sync_seat_quantity
    from app.models.tenant import Tenant

    tenant = Tenant(id=uuid.uuid4(), slug=f"t-{uuid.uuid4().hex[:10]}", name="Free tenant")
    db.add(tenant)
    await db.commit()

    await sync_seat_quantity(db, tenant.id, member_count=20)

    assert fake_stripe_client.v1.subscription_items.created == []


async def test_sync_seat_quantity_noop_when_billing_unconfigured(db, monkeypatch):
    from app import config
    from app.routers.billing import sync_seat_quantity

    monkeypatch.setattr(config.settings, "STRIPE_SECRET_KEY", "")
    tenant, _ = await _make_team_tenant_with_subscription(db, extra_seats=0)

    # Must not raise even though there's no real Stripe client to use.
    await sync_seat_quantity(db, tenant.id, member_count=20)


async def test_accept_invite_syncs_seat_quantity(
    client, tenant_factory, allow_admin, no_smtp, fake_stripe_client, db
):
    from sqlalchemy import select
    from app.models.invite import Invite
    from app.models.tenant import Tenant

    acct = await tenant_factory()
    tenant = await db.get(Tenant, acct["tenant"].id)
    tenant.billing_plan = "team"
    await db.commit()
    await _attach_team_subscription(db, tenant.id, extra_seats=0)

    email = f"teammate-{uuid.uuid4().hex[:10]}@example.com"
    await client.post("/invites", json={"email": email}, headers=acct["headers"])
    invite = await db.scalar(select(Invite).where(Invite.email == email))

    resp = await client.post(
        f"/invites/{invite.token}/accept",
        json={"display_name": "Teammate", "password": "pw-123456"},
    )
    assert resp.status_code == 200
    # 2 members now (the original admin + the new teammate) — still within
    # the included 5 seats, so no seat item should be created.
    assert fake_stripe_client.v1.subscription_items.created == []


async def _add_second_member(db, tenant_id):
    from app.core.auth import hash_password
    from app.models.user import User

    suffix = uuid.uuid4().hex[:10]
    user = User(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        email=f"second-{suffix}@example.com",
        password_hash=hash_password("pw-123456"),
        display_name="Second Member",
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@requires_real_authz
async def test_remove_member_requires_admin(client, tenant_factory):
    acct = await tenant_factory()
    other = await tenant_factory()
    resp = await client.delete(
        f"/invites/members/{other['user'].id}", headers=acct["headers"]
    )
    assert resp.status_code == 403


async def test_remove_member_rejects_removing_self(client, tenant_factory, allow_admin):
    acct = await tenant_factory()
    resp = await client.delete(
        f"/invites/members/{acct['user'].id}", headers=acct["headers"]
    )
    assert resp.status_code == 409


async def test_remove_member_rejects_removing_an_admin(
    client, tenant_factory, monkeypatch, db
):
    from app.core import authz

    acct = await tenant_factory()
    second = await _add_second_member(db, acct["tenant"].id)

    # Both the caller and the target read as admin — the caller passes
    # _assert_tenant_admin, and the target's own admin-check must then
    # block the removal.
    async def _both_admin(user_id, relation, object_id):
        return True

    monkeypatch.setattr(authz.authz_client, "check", _both_admin)

    resp = await client.delete(
        f"/invites/members/{second.id}", headers=acct["headers"]
    )
    assert resp.status_code == 409


async def test_remove_member_succeeds_for_a_non_admin_target(
    client, tenant_factory, monkeypatch, db, fake_stripe_client
):
    from app.core import authz

    acct = await tenant_factory()
    second = await _add_second_member(db, acct["tenant"].id)
    # Caller is admin; the second member is NOT — removal must succeed.
    monkeypatch.setattr(
        authz.authz_client, "check", _admin_only_for(str(acct["user"].id))
    )

    resp = await client.delete(
        f"/invites/members/{second.id}", headers=acct["headers"]
    )
    assert resp.status_code == 204

    listed = await client.get("/invites/members", headers=acct["headers"])
    emails = {m["email"] for m in listed.json()}
    assert second.email not in emails


async def _attach_team_subscription(db, tenant_id, extra_seats=0, seat_item_id=None):
    from app.models.subscription import Subscription, SubscriptionStatus

    now = datetime.now(timezone.utc)
    sub = Subscription(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        stripe_subscription_id=f"sub_{uuid.uuid4().hex[:10]}",
        stripe_price_id="price_team_test",
        plan="team",
        status=SubscriptionStatus.ACTIVE,
        current_period_start=now,
        current_period_end=now + timedelta(days=30),
        extra_seats=extra_seats,
        stripe_seat_item_id=seat_item_id,
    )
    db.add(sub)
    await db.commit()
    return sub
