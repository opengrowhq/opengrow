"""Integration tests for credit-gated generation creation."""

from types import SimpleNamespace

import pytest


@pytest.fixture
def allow_writer(monkeypatch):
    """Stub authz — this repo's local dev environment has no OpenFGA store
    configured, so authz.check()/bind_resource_to_tenant() always fail
    closed here regardless of the real permission logic being tested (see
    test_integration_billing.py)."""
    from app.core import authz

    async def _allow(user_id: str, relation: str, object_id: str) -> bool:
        return True

    async def _noop(*args, **kwargs) -> None:
        return None

    monkeypatch.setattr(authz.authz_client, "check", _allow)
    monkeypatch.setattr(authz.authz_client, "bind_resource_to_tenant", _noop)


@pytest.fixture
def no_celery(monkeypatch):
    from app.workers import tasks

    monkeypatch.setattr(
        tasks.run_generation, "delay", lambda *a, **k: SimpleNamespace(id="test-task")
    )


async def test_free_tenant_generation_not_credit_gated(
    client, tenant_factory, allow_writer, no_celery
):
    """Free tier isn't part of the credit system — a zero balance must not
    block it."""
    acct = await tenant_factory()
    resp = await client.post(
        "/generations", json={"brief": "write a tweet"}, headers=acct["headers"]
    )
    assert resp.status_code == 202


async def test_paid_tenant_with_credits_can_generate(
    client, tenant_factory, db, allow_writer, no_celery
):
    from sqlalchemy import select
    from app.models.tenant import Tenant

    acct = await tenant_factory()
    tenant = await db.get(Tenant, acct["tenant"].id)
    tenant.billing_plan = "pro"
    tenant.credit_balance_cents = 100
    await db.commit()

    resp = await client.post(
        "/generations", json={"brief": "write a tweet"}, headers=acct["headers"]
    )
    assert resp.status_code == 202

    row = await db.execute(
        select(Tenant)
        .where(Tenant.id == acct["tenant"].id)
        .execution_options(populate_existing=True)
    )
    assert row.scalar_one().credit_balance_cents == 95  # 100 - GENERATION_COST_CENTS


async def test_paid_tenant_without_credits_gets_402(
    client, tenant_factory, db, allow_writer, no_celery
):
    from app.models.tenant import Tenant

    acct = await tenant_factory()
    tenant = await db.get(Tenant, acct["tenant"].id)
    tenant.billing_plan = "pro"
    tenant.credit_balance_cents = 0
    await db.commit()

    resp = await client.post(
        "/generations", json={"brief": "write a tweet"}, headers=acct["headers"]
    )
    assert resp.status_code == 402


async def test_insufficient_credit_generation_is_never_created(
    client, tenant_factory, db, allow_writer, no_celery
):
    """A rejected debit must not leave a partially-created Generation row."""
    from sqlalchemy import select
    from app.models.generation import Generation
    from app.models.tenant import Tenant

    acct = await tenant_factory()
    tenant = await db.get(Tenant, acct["tenant"].id)
    tenant.billing_plan = "team"
    tenant.credit_balance_cents = 2  # less than GENERATION_COST_CENTS (5)
    await db.commit()

    resp = await client.post(
        "/generations", json={"brief": "write a tweet"}, headers=acct["headers"]
    )
    assert resp.status_code == 402

    row = await db.execute(
        select(Generation).where(Generation.tenant_id == acct["tenant"].id)
    )
    assert row.first() is None
