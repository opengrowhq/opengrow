"""Tests for the orchestrator: API endpoints + the pipeline logic."""

from uuid import UUID, uuid4

import pytest

from app.core import orchestrator
from app.models.content_piece import ContentPiece
from app.models.generation import GenerationStatus
from app.models.orchestrator import OrchestratorRun, OrchestratorRunStatus
from app.models.tenant import Tenant
from app.models.user import User


# ---- API layer (async, Celery neutralized) --------------------------------


async def test_create_run_persists_and_meters(client, tenant_factory, no_celery):
    acct = await tenant_factory()
    h = acct["headers"]

    run = await client.post(
        "/orchestrator/runs", json={"brief": "write a launch post"}, headers=h
    )
    assert run.status_code == 202
    body = run.json()
    assert body["status"] == "QUEUED"
    run_id = body["run_id"]

    got = await client.get(f"/orchestrator/runs/{run_id}", headers=h)
    assert got.status_code == 200
    assert got.json()["run_id"] == run_id

    summary = await client.get("/usage/summary", headers=h)
    assert "orchestrator_run" in {k["kind"] for k in summary.json()["by_kind"]}


async def test_run_not_found(client, tenant_factory):
    acct = await tenant_factory()
    resp = await client.get(
        "/orchestrator/runs/00000000-0000-0000-0000-000000000000",
        headers=acct["headers"],
    )
    assert resp.status_code == 404


async def test_run_is_tenant_scoped(client, tenant_factory, no_celery):
    a = await tenant_factory()
    b = await tenant_factory()
    run_id = (
        await client.post(
            "/orchestrator/runs", json={"brief": "x"}, headers=a["headers"]
        )
    ).json()["run_id"]
    resp = await client.get(f"/orchestrator/runs/{run_id}", headers=b["headers"])
    assert resp.status_code == 404


async def test_run_requires_auth(client):
    assert (
        await client.post("/orchestrator/runs", json={"brief": "x"})
    ).status_code == 401


async def test_create_article_run_persists_pipeline_details(
    client, db, tenant_factory, no_celery
):
    acct = await tenant_factory()
    resp = await client.post(
        "/orchestrator/runs",
        json={
            "brief": "",
            "article": {"topic": "Compounding", "length_words": 800},
            "pause_for_outline_approval": True,
            "auto_approve": True,
        },
        headers=acct["headers"],
    )
    assert resp.status_code == 202
    body = resp.json()
    assert body["status"] == "QUEUED"

    run = await db.get(OrchestratorRun, UUID(body["run_id"]))
    assert run.details["article"]["topic"] == "Compounding"
    assert run.details["pause_for_outline_approval"] is True
    assert run.details["auto_approve"] is True
    assert run.brief == "Compounding"  # falls back to the topic


async def test_list_runs_returns_tenant_runs_newest_first(
    client, tenant_factory, no_celery
):
    acct = await tenant_factory()
    h = acct["headers"]
    await client.post("/orchestrator/runs", json={"brief": "first"}, headers=h)
    await client.post("/orchestrator/runs", json={"brief": "second"}, headers=h)

    resp = await client.get("/orchestrator/runs", headers=h)
    assert resp.status_code == 200
    assert len(resp.json()) == 2


async def _force_run_state(db, run_id, status, details=None):
    run = await db.get(OrchestratorRun, UUID(run_id))
    run.status = status
    if details is not None:
        run.details = details
    await db.commit()
    return run


async def test_approve_outline_submits_edits_and_redispatches(
    client, db, tenant_factory, no_celery
):
    acct = await tenant_factory()
    h = acct["headers"]
    run_id = (
        await client.post(
            "/orchestrator/runs",
            json={"brief": "", "article": {"topic": "Compounding"}},
            headers=h,
        )
    ).json()["run_id"]
    await _force_run_state(
        db,
        run_id,
        OrchestratorRunStatus.AWAITING_OUTLINE_APPROVAL,
        details={
            "article": {"topic": "Compounding"},
            "sections": [{"heading": "Old", "points": []}],
        },
    )

    resp = await client.post(
        f"/orchestrator/runs/{run_id}/outline/approve",
        json={"outline": [{"heading": "Edited", "points": ["a", "b"]}]},
        headers=h,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "QUEUED"
    assert body["step"] == "draft"
    assert body["outline"] == [{"heading": "Edited", "points": ["a", "b"]}]


async def test_approve_outline_rejects_wrong_state(client, tenant_factory, no_celery):
    acct = await tenant_factory()
    h = acct["headers"]
    run_id = (
        await client.post("/orchestrator/runs", json={"brief": "x"}, headers=h)
    ).json()["run_id"]
    resp = await client.post(
        f"/orchestrator/runs/{run_id}/outline/approve",
        json={"outline": [{"heading": "A", "points": []}]},
        headers=h,
    )
    assert resp.status_code == 409


async def test_approve_outline_validates_payload(client, db, tenant_factory, no_celery):
    acct = await tenant_factory()
    h = acct["headers"]
    run_id = (
        await client.post("/orchestrator/runs", json={"brief": "x"}, headers=h)
    ).json()["run_id"]
    await _force_run_state(db, run_id, OrchestratorRunStatus.AWAITING_OUTLINE_APPROVAL)

    resp = await client.post(
        f"/orchestrator/runs/{run_id}/outline/approve",
        json={"outline": [{"heading": "  ", "points": []}]},
        headers=h,
    )
    assert resp.status_code == 422

    resp = await client.post(
        f"/orchestrator/runs/{run_id}/outline/approve",
        json={"outline": []},
        headers=h,
    )
    assert resp.status_code == 422


async def test_resume_failed_run_redispatches(client, db, tenant_factory, no_celery):
    acct = await tenant_factory()
    h = acct["headers"]
    run_id = (
        await client.post("/orchestrator/runs", json={"brief": "x"}, headers=h)
    ).json()["run_id"]
    await _force_run_state(db, run_id, OrchestratorRunStatus.FAILED)

    resp = await client.post(f"/orchestrator/runs/{run_id}/resume", headers=h)
    assert resp.status_code == 200
    assert resp.json()["status"] == "QUEUED"
    assert resp.json()["error_message"] is None


async def test_resume_rejects_non_failed_run(client, tenant_factory, no_celery):
    acct = await tenant_factory()
    h = acct["headers"]
    run_id = (
        await client.post("/orchestrator/runs", json={"brief": "x"}, headers=h)
    ).json()["run_id"]
    resp = await client.post(f"/orchestrator/runs/{run_id}/resume", headers=h)
    assert resp.status_code == 409


# ---- Pipeline logic (sync, LLM monkeypatched) -----------------------------


def _seed_run(
    sync_db,
    brief="Write a launch post",
    billing_plan="free",
    credit_balance_cents=0,
):
    tenant = Tenant(
        id=uuid4(),
        slug=f"orch-{uuid4().hex[:8]}",
        name="Orch",
        billing_plan=billing_plan,
        credit_balance_cents=credit_balance_cents,
    )
    sync_db.add(tenant)
    sync_db.commit()
    user = User(
        id=uuid4(),
        tenant_id=tenant.id,
        email=f"{uuid4().hex[:8]}@ex.com",
        password_hash="x",
        display_name="U",
    )
    sync_db.add(user)
    sync_db.commit()
    run = OrchestratorRun(
        id=uuid4(),
        tenant_id=tenant.id,
        user_id=user.id,
        brief=brief,
        status=OrchestratorRunStatus.QUEUED,
    )
    sync_db.add(run)
    sync_db.commit()
    return run


def test_execute_run_generates_and_promotes(sync_db, monkeypatch):
    monkeypatch.setattr(
        orchestrator,
        "_generate_text",
        lambda db, gen, brief, model: "generated body copy",
    )
    run = _seed_run(sync_db)

    assert orchestrator.execute_run(sync_db, run.id) == "ok"

    sync_db.refresh(run)
    assert run.status == OrchestratorRunStatus.COMPLETE
    assert run.step == "done"
    assert run.generation_id is not None
    assert run.content_piece_id is not None

    cp = sync_db.get(ContentPiece, run.content_piece_id)
    assert cp.body == "generated body copy"
    assert cp.status.value == "DRAFT"
    assert cp.source_generation_id == run.generation_id

    from app.models.generation import Generation

    gen = sync_db.get(Generation, run.generation_id)
    assert gen.status == GenerationStatus.COMPLETE


def test_execute_run_auto_publishes_when_configured(sync_db, monkeypatch):
    from app.models.content_piece import ContentStatus
    from app.models.publication import Publication

    monkeypatch.setattr(
        orchestrator, "_generate_text", lambda db, gen, brief, model: "body"
    )
    published = {}

    def fake_publish(channel, title, body, config):
        published.update(channel=channel, title=title)
        return {"url": "https://x.com/i/web/status/1", "external_ref": "tweet 1"}

    monkeypatch.setattr(orchestrator, "_publish", fake_publish)

    run = _seed_run(sync_db)
    run.publish_channel = "X"
    run.publish_config = {"access_token": "tok"}
    sync_db.commit()

    assert orchestrator.execute_run(sync_db, run.id) == "ok"
    assert published["channel"] == "X"

    sync_db.refresh(run)
    assert run.status == OrchestratorRunStatus.COMPLETE
    cp = sync_db.get(ContentPiece, run.content_piece_id)
    assert cp.status == ContentStatus.PUBLISHED

    pub = sync_db.query(Publication).filter(Publication.content_piece_id == cp.id).one()
    assert pub.external_ref == "tweet 1"


def test_execute_run_marks_failed_on_llm_error(sync_db, monkeypatch):
    def boom(db, gen, brief, model):
        raise RuntimeError("llm down")

    monkeypatch.setattr(orchestrator, "_generate_text", boom)
    run = _seed_run(sync_db)

    with pytest.raises(RuntimeError):
        orchestrator.execute_run(sync_db, run.id)

    sync_db.refresh(run)
    assert run.status == OrchestratorRunStatus.FAILED
    assert "llm down" in run.error_message


# ---- Article pipeline (design C): pause, resume, guarded publish ----------


def _seed_article_run(
    sync_db,
    pause=True,
    auto_approve=False,
    publish_channel=None,
    billing_plan="free",
    credit_balance_cents=0,
):
    run = _seed_run(
        sync_db,
        brief="Article about compounding",
        billing_plan=billing_plan,
        credit_balance_cents=credit_balance_cents,
    )
    run.details = {
        "article": {
            "topic": "Compounding",
            "length_words": 800,
            "slug": "compounding",
            "tags": ["seo"],
        },
        "pause_for_outline_approval": pause,
        "auto_approve": auto_approve,
    }
    if publish_channel:
        run.publish_channel = publish_channel
    sync_db.commit()
    return run


def _fake_article_llm(monkeypatch, fail_on_kind=None):
    calls = []

    def fake(db, gen, model):
        kind = (gen.metadata_json or {}).get("kind")
        calls.append(kind)
        if kind == fail_on_kind:
            raise RuntimeError(f"llm down during {kind}")
        if kind == "article_outline":
            return "## Intro\n- hook\n\n## Body\n- point"
        return "# Draft body"

    monkeypatch.setattr(orchestrator, "_generate_article", fake)
    return calls


def _generations(sync_db, run):
    from app.models.generation import Generation

    return (
        sync_db.query(Generation)
        .filter(Generation.tenant_id == run.tenant_id)
        .order_by(Generation.created_at)
        .all()
    )


def test_article_run_pauses_then_completes_after_approval(sync_db, monkeypatch):
    _fake_article_llm(monkeypatch)
    run = _seed_article_run(sync_db, pause=True)

    assert orchestrator.execute_run(sync_db, run.id) == "awaiting-outline-approval"

    sync_db.refresh(run)
    assert run.status == OrchestratorRunStatus.AWAITING_OUTLINE_APPROVAL
    assert run.details["sections"] == [
        {"heading": "Intro", "points": ["hook"]},
        {"heading": "Body", "points": ["point"]},
    ]

    # The approve endpoint's worker-side effect: edited outline + re-dispatch.
    run.details = {**run.details, "sections": [{"heading": "Edited", "points": ["x"]}]}
    run.status = OrchestratorRunStatus.QUEUED
    run.step = "draft"
    sync_db.commit()

    assert orchestrator.execute_run(sync_db, run.id) == "ok"

    sync_db.refresh(run)
    assert run.status == OrchestratorRunStatus.COMPLETE
    gens = _generations(sync_db, run)
    assert [g.metadata_json["kind"] for g in gens] == [
        "article_outline",
        "article_draft",
    ]
    assert str(gens[1].parent_generation_id) == str(gens[0].id)
    assert gens[1].metadata_json["outline"] == [{"heading": "Edited", "points": ["x"]}]

    cp = sync_db.get(ContentPiece, run.content_piece_id)
    assert cp.format == "blog_post"
    assert cp.status.value == "DRAFT"
    assert cp.body == "# Draft body"
    assert cp.metadata_json["article"]["slug"] == "compounding"


def test_article_run_unattended_completes_in_one_pass(sync_db, monkeypatch):
    _fake_article_llm(monkeypatch)
    run = _seed_article_run(sync_db, pause=False)

    assert orchestrator.execute_run(sync_db, run.id) == "ok"

    sync_db.refresh(run)
    assert run.status == OrchestratorRunStatus.COMPLETE
    assert run.step == "done"


def test_article_publish_is_skipped_without_approval(sync_db, monkeypatch):
    from app.models.publication import Publication

    _fake_article_llm(monkeypatch)
    published = {}
    monkeypatch.setattr(
        orchestrator,
        "_publish",
        lambda channel, title, body, config: published.setdefault("called", True),
    )
    run = _seed_article_run(sync_db, pause=False, publish_channel="X")

    assert orchestrator.execute_run(sync_db, run.id) == "ok"

    sync_db.refresh(run)
    cp = sync_db.get(ContentPiece, run.content_piece_id)
    assert cp.status.value == "DRAFT"  # never force-published
    assert run.details["publish_note"] == "skipped: content not approved"
    assert "called" not in published
    assert (
        sync_db.query(Publication).filter(Publication.content_piece_id == cp.id).count()
        == 0
    )


def test_article_auto_approve_drives_the_matrix_and_publishes(sync_db, monkeypatch):
    _fake_article_llm(monkeypatch)
    monkeypatch.setattr(
        orchestrator,
        "_publish",
        lambda channel, title, body, config: {
            "url": "https://x.com/1",
            "external_ref": "t1",
        },
    )
    run = _seed_article_run(
        sync_db, pause=False, auto_approve=True, publish_channel="X"
    )

    assert orchestrator.execute_run(sync_db, run.id) == "ok"

    sync_db.refresh(run)
    cp = sync_db.get(ContentPiece, run.content_piece_id)
    assert cp.status.value == "PUBLISHED"
    assert run.details["approvals"] == ["IN_REVIEW", "APPROVED"]


def test_article_failed_run_resumes_at_the_failing_step(sync_db, monkeypatch):
    calls = _fake_article_llm(monkeypatch, fail_on_kind="article_draft")
    run = _seed_article_run(sync_db, pause=False)

    with pytest.raises(RuntimeError):
        orchestrator.execute_run(sync_db, run.id)

    sync_db.refresh(run)
    assert run.status == OrchestratorRunStatus.FAILED
    assert run.step == "draft"
    assert len(_generations(sync_db, run)) == 2  # outline done, draft failed

    # Fix the LLM and re-enter: the outline must NOT be regenerated.
    _fake_article_llm(monkeypatch)
    assert orchestrator.execute_run(sync_db, run.id) == "ok"

    sync_db.refresh(run)
    assert run.status == OrchestratorRunStatus.COMPLETE
    gens = _generations(sync_db, run)
    assert len(gens) == 2
    assert calls == ["article_outline", "article_draft"]


# ---- Credit gating: orchestrator-driven generations must be billed, same
# as app.routers.generations.create_generation (see feature/orchestrator-
# credit-gating) --------------------------------------------------------


def test_legacy_run_holds_and_settles_credits_on_pro_tenant(sync_db, monkeypatch):
    from app.models.generation import Generation

    async def _fake_chat_completion(**kwargs):
        return "generated body copy", {
            "model": "gpt-4o-mini",
            "usage": {
                "prompt_tokens": 50,
                "completion_tokens": 50,
                "total_tokens": 100,
            },
            "choices": [],
        }

    monkeypatch.setattr(orchestrator, "chat_completion", _fake_chat_completion)
    run = _seed_run(sync_db, billing_plan="pro", credit_balance_cents=100)

    assert orchestrator.execute_run(sync_db, run.id) == "ok"

    sync_db.refresh(run)
    tenant = sync_db.get(Tenant, run.tenant_id)
    # Held some positive amount up front, then the tiny fake completion's
    # real cost rounds to ~0c, so nearly the full hold is refunded back.
    assert 0 < tenant.credit_balance_cents <= 100

    gen = sync_db.get(Generation, run.generation_id)
    assert gen.status == GenerationStatus.COMPLETE
    # The hold marker is cleared once settled (idempotent re-entry guard).
    assert "credit_hold_cents" not in (gen.metadata_json or {})


def test_legacy_run_refunds_full_hold_on_llm_failure(sync_db, monkeypatch):
    from app.models.generation import Generation

    async def _failing_chat_completion(**kwargs):
        raise RuntimeError("llm down")

    monkeypatch.setattr(orchestrator, "chat_completion", _failing_chat_completion)
    run = _seed_run(sync_db, billing_plan="pro", credit_balance_cents=100)

    with pytest.raises(RuntimeError):
        orchestrator.execute_run(sync_db, run.id)

    sync_db.refresh(run)
    tenant = sync_db.get(Tenant, run.tenant_id)
    assert tenant.credit_balance_cents == 100  # fully refunded, nothing charged

    gen = sync_db.get(Generation, run.generation_id)
    assert gen.status == GenerationStatus.FAILED
    assert "credit_hold_cents" not in (gen.metadata_json or {})


def test_legacy_run_free_tenant_is_not_credit_gated(sync_db, monkeypatch):
    monkeypatch.setattr(
        orchestrator, "_generate_text", lambda db, gen, brief, model: "body"
    )
    run = _seed_run(sync_db, billing_plan="free", credit_balance_cents=0)

    assert orchestrator.execute_run(sync_db, run.id) == "ok"

    sync_db.refresh(run)
    tenant = sync_db.get(Tenant, run.tenant_id)
    assert tenant.credit_balance_cents == 0  # never touched


def _fake_chat_completion_for_article(fail_on_model_call=None):
    calls = {"n": 0}

    async def _fake(**kwargs):
        calls["n"] += 1
        if fail_on_model_call == calls["n"]:
            raise RuntimeError(f"llm down on call {calls['n']}")
        # First call is the outline, second is the draft — same shape works
        # for both since only build_generation_messages' prompt differs.
        text = (
            "## Intro\n- hook\n\n## Body\n- point" if calls["n"] == 1 else "# Draft body"
        )
        return text, {
            "model": "gpt-4o-mini",
            "usage": {
                "prompt_tokens": 50,
                "completion_tokens": 50,
                "total_tokens": 100,
            },
            "choices": [],
        }

    return _fake, calls


def test_article_run_holds_and_settles_credits_on_pro_tenant(sync_db, monkeypatch):
    fake, _ = _fake_chat_completion_for_article()
    monkeypatch.setattr(orchestrator, "chat_completion", fake)
    run = _seed_article_run(
        sync_db, pause=False, billing_plan="pro", credit_balance_cents=100
    )

    assert orchestrator.execute_run(sync_db, run.id) == "ok"

    sync_db.refresh(run)
    tenant = sync_db.get(Tenant, run.tenant_id)
    # Two generations (outline + draft) were each held then settled — some
    # credits were spent and some refunded, balance stays below the start.
    assert 0 < tenant.credit_balance_cents <= 100

    gens = _generations(sync_db, run)
    assert len(gens) == 2
    for g in gens:
        assert "credit_hold_cents" not in (g.metadata_json or {})


def test_article_run_retry_after_failure_holds_its_own_credits_not_free_or_doubled(
    sync_db, monkeypatch
):
    """Regression test for the bug this branch fixes: a failed generation's
    hold must be refunded exactly once (not once per retry attempt, like the
    Celery-level bug fixed in app.workers.tasks.run_generation), AND a
    retried attempt on the same row must get its own fresh hold rather than
    running unbilled just because the first hold was already refunded."""
    from app.models.generation import Generation

    fake, calls = _fake_chat_completion_for_article(fail_on_model_call=2)
    monkeypatch.setattr(orchestrator, "chat_completion", fake)
    run = _seed_article_run(
        sync_db, pause=False, billing_plan="pro", credit_balance_cents=100
    )

    with pytest.raises(RuntimeError):
        orchestrator.execute_run(sync_db, run.id)

    sync_db.refresh(run)
    tenant = sync_db.get(Tenant, run.tenant_id)
    gens = _generations(sync_db, run)
    assert len(gens) == 2  # outline settled, draft created+failed
    outline_gen, draft_gen = gens
    assert outline_gen.status == GenerationStatus.COMPLETE
    assert draft_gen.status == GenerationStatus.FAILED
    # Outline was held+settled (refunded to ~0 real cost); draft's hold was
    # refunded in full on failure — balance should be back near the start,
    # not below it (no uncollected charge) and not above it (no over-refund).
    assert 0 < tenant.credit_balance_cents <= 100
    balance_after_failure = tenant.credit_balance_cents

    # Re-enter (simulates a Celery retry of run_orchestrator): the draft
    # generation is retried on the SAME row.
    fake2, _ = _fake_chat_completion_for_article()
    monkeypatch.setattr(orchestrator, "chat_completion", fake2)
    assert orchestrator.execute_run(sync_db, run.id) == "ok"

    sync_db.refresh(run)
    sync_db.refresh(tenant)
    assert run.status == OrchestratorRunStatus.COMPLETE
    gens_after = _generations(sync_db, run)
    assert len(gens_after) == 2  # still the same two rows, no duplicate outline
    assert gens_after[1].id == draft_gen.id
    assert gens_after[1].status == GenerationStatus.COMPLETE
    # The retry's own hold was debited and then settled — balance moved
    # (not identical to balance_after_failure, proving the retry was
    # actually billed, not a free ride), and never went negative/wrong.
    assert 0 < tenant.credit_balance_cents <= balance_after_failure
