"""Integration tests for the prepaid credit balance (debit/grant)."""

import asyncio

import pytest
from sqlalchemy import select

from app.core.credits import (
    InsufficientCreditsError,
    debit_credits,
    grant_credits,
)
from app.models.tenant import Tenant

_TEST_COST_CENTS = 5  # arbitrary — these tests exercise the debit/grant
# mechanism itself, not any specific pricing.


async def test_debit_credits_rejects_non_positive_cost(db, tenant_factory):
    acct = await tenant_factory()
    with pytest.raises(ValueError):
        await debit_credits(db, tenant_id=acct["tenant"].id, cost_cents=0)
    with pytest.raises(ValueError):
        await debit_credits(db, tenant_id=acct["tenant"].id, cost_cents=-1)


async def test_grant_credits_rejects_non_positive_amount(db, tenant_factory):
    acct = await tenant_factory()
    with pytest.raises(ValueError):
        await grant_credits(db, tenant_id=acct["tenant"].id, amount_cents=0)


async def test_grant_credits_increases_balance(db, tenant_factory):
    acct = await tenant_factory()
    new_balance = await grant_credits(
        db, tenant_id=acct["tenant"].id, amount_cents=5000
    )
    assert new_balance == 5000

    row = await db.execute(
        select(Tenant)
        .where(Tenant.id == acct["tenant"].id)
        .execution_options(populate_existing=True)
    )
    assert row.scalar_one().credit_balance_cents == 5000


async def test_debit_credits_decreases_balance(db, tenant_factory):
    acct = await tenant_factory()
    await grant_credits(db, tenant_id=acct["tenant"].id, amount_cents=100)

    new_balance = await debit_credits(
        db, tenant_id=acct["tenant"].id, cost_cents=_TEST_COST_CENTS
    )
    assert new_balance == 100 - _TEST_COST_CENTS


async def test_debit_credits_raises_402_when_insufficient(db, tenant_factory):
    acct = await tenant_factory()
    # Balance starts at 0 (migration default).
    with pytest.raises(InsufficientCreditsError) as exc_info:
        await debit_credits(
            db, tenant_id=acct["tenant"].id, cost_cents=_TEST_COST_CENTS
        )
    assert exc_info.value.status_code == 402


async def test_debit_credits_never_goes_negative(db, tenant_factory):
    acct = await tenant_factory()
    await grant_credits(db, tenant_id=acct["tenant"].id, amount_cents=3)

    with pytest.raises(InsufficientCreditsError):
        await debit_credits(db, tenant_id=acct["tenant"].id, cost_cents=5)

    row = await db.execute(
        select(Tenant)
        .where(Tenant.id == acct["tenant"].id)
        .execution_options(populate_existing=True)
    )
    # The failed debit must not have partially applied.
    assert row.scalar_one().credit_balance_cents == 3


async def test_concurrent_debits_cannot_overdraw_balance(engine, db, tenant_factory):
    """Race-safety: N concurrent debits against a balance that can only
    cover fewer than N of them must never let the balance go negative —
    this is exactly the TOCTOU bug an atomic conditional UPDATE prevents."""
    from sqlalchemy.ext.asyncio import async_sessionmaker

    acct = await tenant_factory()
    tenant_id = acct["tenant"].id
    await grant_credits(db, tenant_id=tenant_id, amount_cents=10)

    Session = async_sessionmaker(engine, expire_on_commit=False)

    async def _try_debit():
        async with Session() as session:
            try:
                await debit_credits(session, tenant_id=tenant_id, cost_cents=5)
                return True
            except InsufficientCreditsError:
                return False

    results = await asyncio.gather(*[_try_debit() for _ in range(5)])
    assert sum(results) == 2  # exactly 10 cents / 5 cents each succeed

    row = await db.execute(
        select(Tenant)
        .where(Tenant.id == tenant_id)
        .execution_options(populate_existing=True)
    )
    assert row.scalar_one().credit_balance_cents == 0
