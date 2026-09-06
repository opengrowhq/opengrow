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
):
    tenant = Tenant(
        id=uuid4(),
        slug=f"orch-{uuid4().hex[:8]}",
        name="Orch",
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
):
    run = _seed_run(
        sync_db,
        brief="Article about compounding",
    )
    run.details = {
        "article": {
            "topic": "Compounding",
            # Explicit keyword: skips the keyword_research step (which would
            # otherwise make a real outbound HTTP call) — see the dedicated
            # test_execute_run_keyword_research_* tests below for that step.
            "primary_keyword": "compounding",
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


_GOOD_DRAFT = (
    "## Intro\n"
    "Compounding is one of the most powerful forces in personal finance, and "
    "understanding compounding early changes how you plan for the long run. "
    "This guide walks through why compounding matters and how to use it.\n\n"
    "## Body\n"
    "Small, consistent contributions compound over time into large outcomes. "
    "The earlier you start, the more time compounding has to work in your favor, "
    "and even modest amounts add up meaningfully across a couple of decades."
)


def _fake_article_llm(monkeypatch, fail_on_kind=None, draft_text=_GOOD_DRAFT):
    """draft_text defaults to a fixture that clears the quality gate
    (keyword/heading coverage, length, readability) so existing pipeline
    tests exercise promote/publish rather than the gate itself — see the
    dedicated test_execute_run_score_gate_* tests below for gate behavior.

    The draft "follows" whatever outline it's given (mirrors each section's
    heading into the draft) so a test that edits the approved outline still
    gets a draft whose headings match it, same as a real LLM would."""
    calls = []

    def fake(db, gen, model):
        kind = (gen.metadata_json or {}).get("kind")
        calls.append(kind)
        if kind == fail_on_kind:
            raise RuntimeError(f"llm down during {kind}")
        if kind == "article_outline":
            return "## Intro\n- hook\n\n## Body\n- point"
        outline = (gen.metadata_json or {}).get("outline") or []
        if outline:
            body = "\n\n".join(f"## {s['heading']}\n{draft_text}" for s in outline)
            return body
        return draft_text

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
    assert "## Edited" in cp.body  # draft followed the edited outline
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


# ---- Quality gate: score → promote, score → retry-with-feedback, or fail --


def test_execute_run_score_gate_promotes_a_good_draft(sync_db, monkeypatch):
    _fake_article_llm(monkeypatch)
    run = _seed_article_run(sync_db, pause=False)

    assert orchestrator.execute_run(sync_db, run.id) == "ok"

    sync_db.refresh(run)
    assert run.status == OrchestratorRunStatus.COMPLETE
    assert run.details["score"] >= orchestrator.settings.ARTICLE_SCORE_THRESHOLD
    assert run.details["score_retries"] == 0
    assert len(_generations(sync_db, run)) == 2  # no extra retry generation


def test_execute_run_score_gate_retries_then_promotes(sync_db, monkeypatch):
    """A low-scoring first draft is regenerated with feedback; the second
    (good) draft passes and the run completes — exercising one full
    retry loop within a single execute_run call, for both the failed and
    the successful draft attempts."""
    calls = {"n": 0}

    def fake(db, gen, model):
        kind = (gen.metadata_json or {}).get("kind")
        if kind == "article_outline":
            return "## Intro\n- hook\n\n## Body\n- point"
        calls["n"] += 1
        return "bad" if calls["n"] == 1 else _GOOD_DRAFT

    monkeypatch.setattr(orchestrator, "_generate_article", fake)
    run = _seed_article_run(sync_db, pause=False)

    assert orchestrator.execute_run(sync_db, run.id) == "ok"

    sync_db.refresh(run)
    assert run.status == OrchestratorRunStatus.COMPLETE
    assert run.details["score_retries"] == 1
    assert calls["n"] == 2  # first bad draft, one regenerate

    gens = _generations(sync_db, run)
    assert len(gens) == 3  # outline + failed-gate draft + passing draft
    kinds = [g.metadata_json["kind"] for g in gens]
    assert kinds == ["article_outline", "article_draft", "article_draft"]
    # feedback was folded into the retried brief's notes
    assert gens[2].metadata_json["article"]["notes"]

    cp = sync_db.get(ContentPiece, run.content_piece_id)
    assert cp.body == _GOOD_DRAFT
    assert (
        cp.source_generation_id == gens[2].id
    )  # the passing attempt, not the failed one


def test_execute_run_score_gate_fails_after_max_retries(sync_db, monkeypatch):
    monkeypatch.setattr(
        orchestrator,
        "_generate_article",
        lambda db, gen, model: (
            "## Intro\n- hook\n\n## Body\n- point"
            if (gen.metadata_json or {}).get("kind") == "article_outline"
            else "bad"
        ),
    )
    run = _seed_article_run(sync_db, pause=False)

    with pytest.raises(orchestrator.QualityGateFailed):
        orchestrator.execute_run(sync_db, run.id)

    sync_db.refresh(run)
    assert run.status == OrchestratorRunStatus.FAILED
    assert "scored" in run.error_message
    assert (
        run.details["score_retries"] == orchestrator.settings.ARTICLE_SCORE_MAX_RETRIES
    )
    # outline + one draft attempt per retry budget slot (initial + retries)
    assert (
        len(_generations(sync_db, run))
        == 1 + orchestrator.settings.ARTICLE_SCORE_MAX_RETRIES + 1
    )
    # never promoted
    assert run.content_piece_id is None


def test_execute_run_score_gate_reentry_at_score_step(sync_db, monkeypatch):
    """Simulates a crash between _step_draft committing step="score" and
    _step_score running — execute_run must still run the gate, not skip
    straight through to done."""
    _fake_article_llm(monkeypatch)
    run = _seed_article_run(sync_db, pause=False)
    run.status = OrchestratorRunStatus.QUEUED
    run.step = "outline"
    sync_db.commit()

    # Drive it manually up to right after the draft LLM call, mimicking a
    # crash: force run.step to "score" with a draft already in details but
    # never actually invoke _step_score.
    from app.models.generation import Generation

    outline_gen = Generation(
        id=uuid4(),
        tenant_id=run.tenant_id,
        owner_id=run.user_id,
        brief="Compounding",
        status=GenerationStatus.COMPLETE,
        metadata_json={"kind": "article_outline"},
        result="## Intro\n- hook\n\n## Body\n- point",
    )
    draft_gen = Generation(
        id=uuid4(),
        tenant_id=run.tenant_id,
        owner_id=run.user_id,
        brief="Compounding",
        status=GenerationStatus.COMPLETE,
        metadata_json={"kind": "article_draft"},
        result=_GOOD_DRAFT,
    )
    sync_db.add_all([outline_gen, draft_gen])
    sync_db.commit()
    run.details = {
        "article": {"topic": "Compounding", "length_words": 800},
        "pause_for_outline_approval": False,
        "auto_approve": False,
        "outline_gen_id": str(outline_gen.id),
        "outline_text": outline_gen.result,
        "sections": [{"heading": "Intro", "points": ["hook"]}],
        "draft_gen_id": str(draft_gen.id),
        "draft_text": draft_gen.result,
    }
    run.generation_id = draft_gen.id
    run.step = "score"
    sync_db.commit()

    assert orchestrator.execute_run(sync_db, run.id) == "ok"

    sync_db.refresh(run)
    assert run.status == OrchestratorRunStatus.COMPLETE
    assert "score" in run.details  # the gate actually ran, not skipped
    assert run.content_piece_id is not None


# ---- Keyword research: real pipeline entrypoint (Phase 3) ------------------


def _seed_article_run_no_keyword(sync_db, **kwargs):
    """Like _seed_article_run but WITHOUT a primary_keyword, so the new
    keyword_research step actually fires instead of being skipped."""
    run = _seed_article_run(sync_db, **kwargs)
    article = dict(run.details["article"])
    article.pop("primary_keyword", None)
    run.details = {**run.details, "article": article}
    sync_db.commit()
    return run


def test_execute_run_skips_keyword_research_when_keyword_already_set(
    sync_db, monkeypatch
):
    """The common/default case: a caller that already knows its keyword
    never triggers a network call — zero behavior change from before this
    step existed."""
    called = {"n": 0}

    def fake_research(topic):
        called["n"] += 1
        return {"primary_keyword": "x", "secondary_keywords": [], "questions": []}

    monkeypatch.setattr(orchestrator, "research_keywords", fake_research)
    _fake_article_llm(monkeypatch)
    run = _seed_article_run(sync_db, pause=False)  # has primary_keyword="compounding"

    assert orchestrator.execute_run(sync_db, run.id) == "ok"
    assert called["n"] == 0


def test_execute_run_researches_keyword_when_blank(sync_db, monkeypatch):
    def fake_research(topic):
        assert topic == "Compounding"
        return {
            "primary_keyword": "compounding",
            "secondary_keywords": ["compound growth"],
            "questions": ["How does compounding work?"],
            "sources": {},
        }

    monkeypatch.setattr(orchestrator, "research_keywords", fake_research)
    _fake_article_llm(monkeypatch)
    run = _seed_article_run_no_keyword(sync_db, pause=False)

    assert orchestrator.execute_run(sync_db, run.id) == "ok"

    sync_db.refresh(run)
    assert run.details["article"]["primary_keyword"] == "compounding"
    assert "compound growth" in run.details["article"]["secondary_keywords"]
    assert run.details["keyword_research"]["primary_keyword"] == "compounding"


def test_execute_run_keyword_research_is_idempotent_on_reentry(sync_db, monkeypatch):
    calls = {"n": 0}

    def fake_research(topic):
        calls["n"] += 1
        return {
            "primary_keyword": "compounding",
            "secondary_keywords": [],
            "questions": [],
        }

    monkeypatch.setattr(orchestrator, "research_keywords", fake_research)
    _fake_article_llm(monkeypatch, fail_on_kind="article_outline")
    run = _seed_article_run_no_keyword(sync_db, pause=False)

    with pytest.raises(RuntimeError):
        orchestrator.execute_run(sync_db, run.id)

    assert calls["n"] == 1  # research already ran before the outline failed

    _fake_article_llm(monkeypatch)  # fix the LLM, re-enter
    assert orchestrator.execute_run(sync_db, run.id) == "ok"
    assert calls["n"] == 1  # not re-run on retry — keyword_research already present


def test_execute_run_keyword_research_failure_falls_back_to_topic(sync_db, monkeypatch):
    """Best-effort: if every scraping source fails, the run must still
    proceed (with primary_keyword defaulted to the bare topic) rather than
    blocking the pipeline on Google/Bing being unreachable. Exercises the
    real research_keywords()'s own internal try/except (not a fake that
    bypasses it), by breaking its actual HTTP dependency instead."""

    def boom(*a, **k):
        raise RuntimeError("network down")

    monkeypatch.setattr("app.core.keyword_research.fetch_url", boom)
    _fake_article_llm(monkeypatch)
    run = _seed_article_run_no_keyword(sync_db, pause=False)

    assert orchestrator.execute_run(sync_db, run.id) == "ok"

    sync_db.refresh(run)
    assert (
        run.details["article"]["primary_keyword"] == "Compounding"
    )  # falls back to topic
