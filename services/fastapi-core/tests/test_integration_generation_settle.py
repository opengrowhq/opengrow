"""Integration test for the hold-and-settle credit reconciliation inside
run_generation — the Celery task where the LLM call actually happens."""

import asyncio
import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from app.models.generation import Generation, GenerationStatus
from app.models.tenant import Tenant
from app.models.user import User
from app.core.auth import hash_password


@pytest.fixture
def worker_sync_db(engine, monkeypatch):
    """Point the worker's module-level _SyncSession at the same test
    database the async fixtures use (it normally binds to the real
    lite/prod DSN at import time, which the test DB isn't)."""
    from app.workers import tasks
    from tests.conftest import _test_sync_dsn
    from sqlalchemy import create_engine

    sync_engine = create_engine(_test_sync_dsn())
    SessionSync = sessionmaker(sync_engine, expire_on_commit=False)
    monkeypatch.setattr(tasks, "_SyncSession", SessionSync)
    yield SessionSync
    sync_engine.dispose()


async def _make_pro_tenant_with_generation(
    db, credit_balance_cents: int, hold_cents: int = 50
):
    """`credit_balance_cents` is the balance BEFORE the hold (what the
    generation flow already debited via debit_credits() when the generation
    was created) — the fixture starts the tenant already short that hold, so
    a settle-time refund is what brings the balance back up."""
    suffix = uuid.uuid4().hex[:10]
    tenant = Tenant(
        id=uuid.uuid4(),
        slug=f"t-{suffix}",
        name=f"Tenant {suffix}",
        billing_plan="pro",
        credit_balance_cents=credit_balance_cents - hold_cents,
    )
    db.add(tenant)
    await db.commit()

    user = User(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        email=f"user-{suffix}@example.com",
        password_hash=hash_password("pw-123456"),
        display_name="Test User",
    )
    db.add(user)
    await db.commit()

    gen = Generation(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        owner_id=user.id,
        brief="write a tweet",
        status=GenerationStatus.QUEUED,
        metadata_json={"model": "gpt-4o-mini", "credit_hold_cents": hold_cents},
    )
    db.add(gen)
    await db.commit()
    await db.refresh(gen)
    return tenant, gen


async def test_run_generation_refunds_the_difference_between_hold_and_real_cost(
    db, worker_sync_db, monkeypatch
):
    from app.workers import tasks

    tenant, gen = await _make_pro_tenant_with_generation(db, credit_balance_cents=100)

    async def _fake_chat_completion(**kwargs):
        return "generated tweet text", {
            "model": "gpt-4o-mini",
            "usage": {
                "prompt_tokens": 50,
                "completion_tokens": 50,
                "total_tokens": 100,
            },
            "choices": [],
        }

    monkeypatch.setattr(tasks, "chat_completion", _fake_chat_completion)
    monkeypatch.setattr(tasks.notify_email, "delay", lambda *a, **k: None)

    # run_generation is a sync Celery task that bridges into asyncio itself
    # (tasks._run) — calling it directly from this async test would nest
    # event loops, so it must run in a separate thread with no running loop.
    # .apply() (not .run()) gives self.retry() a real task request context.
    async_result = await asyncio.to_thread(tasks.run_generation.apply, (str(gen.id),))
    result = async_result.get()
    assert result == "ok"

    row = await db.execute(
        select(Tenant)
        .where(Tenant.id == tenant.id)
        .execution_options(populate_existing=True)
    )
    refreshed = row.scalar_one()
    # Held 50c up front; real cost of this tiny fake completion rounds to
    # 0c, so the full 50c hold is refunded — balance returns to 100.
    assert refreshed.credit_balance_cents == 100

    gen_row = await db.execute(
        select(Generation)
        .where(Generation.id == gen.id)
        .execution_options(populate_existing=True)
    )
    assert gen_row.scalar_one().status == GenerationStatus.COMPLETE


async def test_run_generation_refunds_full_hold_on_failure(
    db, worker_sync_db, monkeypatch
):
    from app.workers import tasks

    tenant, gen = await _make_pro_tenant_with_generation(db, credit_balance_cents=100)

    async def _failing_chat_completion(**kwargs):
        raise RuntimeError("upstream LLM error")

    monkeypatch.setattr(tasks, "chat_completion", _failing_chat_completion)
    monkeypatch.setattr(tasks.notify_email, "delay", lambda *a, **k: None)

    # .apply() runs eagerly but still honors max_retries=2: self.retry()
    # re-invokes the task body synchronously up to 2 more times, so this
    # exercises run_generation 3 times total before giving up and re-raising
    # the original exception (not celery.exceptions.Retry, which only
    # surfaces when a real worker/broker drives the retry). That repetition
    # is exactly what regression-tests the "refund once, not once per retry
    # attempt" fix in run_generation's failure path.
    async_result = await asyncio.to_thread(tasks.run_generation.apply, (str(gen.id),))
    with pytest.raises(RuntimeError, match="upstream LLM error"):
        async_result.get()

    row = await db.execute(
        select(Tenant)
        .where(Tenant.id == tenant.id)
        .execution_options(populate_existing=True)
    )
    # Failed generation: the full 50c hold is refunded, not kept.
    assert row.scalar_one().credit_balance_cents == 100
