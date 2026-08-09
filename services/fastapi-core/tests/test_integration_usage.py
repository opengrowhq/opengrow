"""Integration tests for usage metering (ledger + summary)."""

import pytest
from types import SimpleNamespace


@pytest.fixture
def _no_celery(monkeypatch):
    # Neutralize the Celery dispatch so POST /generations doesn't enqueue a real
    # task (the worker points at a different DB in tests).
    from app.workers import tasks

    monkeypatch.setattr(
        tasks.run_generation, "delay", lambda *a, **k: SimpleNamespace(id="test-task")
    )


async def test_generation_records_usage(client, tenant_factory, _no_celery):
    acct = await tenant_factory()
    h = acct["headers"]

    gen = await client.post("/generations", json={"brief": "write a tweet"}, headers=h)
    assert gen.status_code == 202

    summary = await client.get("/usage/summary", headers=h)
    assert summary.status_code == 200
    body = summary.json()
    assert body["units"] == 1
    assert body["events"] == 1
    assert body["by_kind"][0]["kind"] == "generation"

    listing = await client.get("/usage", headers=h)
    assert listing.status_code == 200
    assert listing.headers["X-Total-Count"] == "1"
    assert listing.json()[0]["ref_type"] == "generation"


async def test_usage_summary_aggregates_by_kind(client, tenant_factory, db):
    from app.core.usage import record_usage

    acct = await tenant_factory()
    tid = acct["tenant"].id
    await record_usage(db, tenant_id=tid, kind="generation", units=1, cost_units=100)
    await record_usage(db, tenant_id=tid, kind="generation", units=1, cost_units=250)
    await record_usage(db, tenant_id=tid, kind="publish", units=1, cost_units=0)

    summary = await client.get("/usage/summary", headers=acct["headers"])
    body = summary.json()
    assert body["units"] == 3
    assert body["cost_units"] == 350
    kinds = {k["kind"]: k for k in body["by_kind"]}
    assert kinds["generation"]["events"] == 2
    assert kinds["generation"]["cost_units"] == 350
    assert kinds["publish"]["events"] == 1


async def test_usage_is_tenant_scoped(client, tenant_factory, db):
    from app.core.usage import record_usage

    a = await tenant_factory()
    b = await tenant_factory()
    await record_usage(db, tenant_id=a["tenant"].id, kind="generation", units=5)

    summary_b = await client.get("/usage/summary", headers=b["headers"])
    assert summary_b.json()["units"] == 0


async def test_usage_requires_auth(client):
    assert (await client.get("/usage/summary")).status_code == 401
