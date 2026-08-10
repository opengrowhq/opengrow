"""Orchestrator pipeline logic (sync, so the Celery worker can drive it).

Two pipelines share the `execute_run` entry point:

- **Legacy generic copy** (no `details["article"]`): generate → promote →
  optional publish, exactly the pre-design-C behavior.
- **Article pipeline** (`details["article"]` set): outline → optional human
  pause (`AWAITING_OUTLINE_APPROVAL`) → draft → promote → guarded publish.

`execute_run` dispatches on `run.step` and every step is idempotent (work
already recorded in `run.details` is not repeated), so a run is safe to
re-enter after a Celery retry or an explicit `/resume`.
"""

from __future__ import annotations

import asyncio
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from app.config import settings
from app.core.article_grounding import ground_article
from app.core.article_metadata import article_content_metadata
from app.core.generation_messages import build_generation_messages
from app.core.litellm_client import chat_completion
from app.core.publishers import PublisherError, get_adapter
from app.core.usage import record_usage_sync
from app.models.content_piece import ContentPiece, ContentStatus
from app.models.generation import Generation, GenerationStatus
from app.models.orchestrator import OrchestratorRun, OrchestratorRunStatus
from app.models.publication import (
    Publication,
    PublicationChannel,
    PublicationStatus,
)

_SYSTEM = "You write concise, high-quality marketing copy."


def _run(coro):
    """Bridge asyncio → sync caller (same semantics as the worker's helper)."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            raise RuntimeError("already running")
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)


def _generate_text(brief: str, model: str) -> str:
    """Run the LLM for the given brief. Isolated so tests can monkeypatch it."""
    content, _resp = _run(
        chat_completion(
            messages=[
                {"role": "system", "content": _SYSTEM},
                {"role": "user", "content": brief},
            ],
            model=model,
        )
    )
    return content


def _title_from_brief(brief: str) -> str:
    first = brief.strip().splitlines()[0] if brief.strip() else "Untitled"
    return (first[:80]).strip() or "Untitled"


def _publish(channel: str, title: str, body: str, config: dict) -> dict:
    """Run a publisher adapter. Isolated so tests can monkeypatch it."""
    adapter = get_adapter(channel)
    if adapter is None:
        raise PublisherError(f"{channel} publishing not implemented")
    return asyncio.run(adapter.publish(title=title, body=body, config=config))


# -----------------------------------------------------------------------------
# Article pipeline (design C)
# -----------------------------------------------------------------------------
def _parse_outline(text: str) -> list[dict]:
    """Parse an LLM outline (## headings + - bullets) into sections.

    Mirrors the frontend's parseOutline so unattended runs can draft without
    a client round-trip.
    """
    sections: list[dict] = []
    for raw in str(text or "").split("\n"):
        line = raw.strip()
        if not line:
            continue
        if line.startswith("#"):
            heading = line.lstrip("#").strip()
            if heading:
                sections.append({"heading": heading, "points": []})
        elif line[:2] in ("- ", "* ") and sections:
            sections[-1]["points"].append(line[2:].strip())
    return sections


def _generate_article(db: Session, gen: Generation, model: str) -> str:
    """Ground + compose + run the LLM for an article generation row."""
    article = (gen.metadata_json or {}).get("article") or {}
    brand, context = ground_article(db, gen.tenant_id, article)
    messages, max_tokens = build_generation_messages(
        db, gen, brand=brand, context=context
    )
    content, _resp = _run(
        chat_completion(messages=messages, model=model, max_tokens=max_tokens)
    )
    return content


def _new_article_generation(
    db: Session,
    run: OrchestratorRun,
    details: dict,
    *,
    kind: str,
    model: str,
    parent_generation_id=None,
    outline: list[dict] | None = None,
) -> Generation:
    article = details["article"]
    metadata = {
        "kind": kind,
        "article": article,
        "model": model,
        "orchestrator_run_id": str(run.id),
    }
    if outline is not None:
        metadata["outline"] = outline
    gen = Generation(
        id=uuid4(),
        tenant_id=run.tenant_id,
        owner_id=run.user_id,
        brief=article.get("topic") or run.brief,
        status=GenerationStatus.QUEUED,
        parent_generation_id=parent_generation_id,
        metadata_json=metadata,
    )
    db.add(gen)
    db.commit()
    record_usage_sync(
        db,
        tenant_id=run.tenant_id,
        kind="generation",
        units=1,
        ref_type="generation",
        ref_id=str(gen.id),
        user_id=run.user_id,
    )
    return gen


def _finish_article_generation(db: Session, gen: Generation, model: str) -> str:
    """Run the LLM for a pending article generation; FAILED the row on error."""
    try:
        text = _generate_article(db, gen, model)
    except Exception:
        gen.status = GenerationStatus.FAILED
        db.commit()
        raise
    gen.result = text
    gen.status = GenerationStatus.COMPLETE
    db.commit()
    return text


def _step_outline(db: Session, run: OrchestratorRun) -> None:
    details = dict(run.details or {})
    model = run.model or settings.DEFAULT_LLM_MODEL
    run.status = OrchestratorRunStatus.GENERATING
    run.step = "outline"
    db.commit()

    gen = None
    if details.get("outline_gen_id"):
        gen = db.get(Generation, UUID(details["outline_gen_id"]))
    if gen is None:
        gen = _new_article_generation(
            db, run, details, kind="article_outline", model=model
        )
        # Assign a NEW dict each time — SQLAlchemy's plain JSONB does not
        # track in-place mutation, and re-assigning the same object is a
        # no-op, so intermediate commits would silently drop keys.
        details = {**details, "outline_gen_id": str(gen.id)}
        run.generation_id = gen.id
        run.details = details
        db.commit()

    if not details.get("outline_text"):
        text = _finish_article_generation(db, gen, model)
        details = {
            **details,
            "outline_text": text,
            "sections": _parse_outline(text),
        }
        run.details = details
        db.commit()

    if details.get("pause_for_outline_approval", True):
        run.status = OrchestratorRunStatus.AWAITING_OUTLINE_APPROVAL
        run.step = "await_outline"
    else:
        run.step = "draft"
    db.commit()


def _step_draft(db: Session, run: OrchestratorRun) -> None:
    details = dict(run.details or {})
    model = run.model or settings.DEFAULT_LLM_MODEL
    run.status = OrchestratorRunStatus.GENERATING
    run.step = "draft"
    db.commit()

    gen = None
    if details.get("draft_gen_id"):
        gen = db.get(Generation, UUID(details["draft_gen_id"]))
    if gen is None:
        gen = _new_article_generation(
            db,
            run,
            details,
            kind="article_draft",
            model=model,
            parent_generation_id=UUID(details["outline_gen_id"]),
            outline=details.get("sections") or [],
        )
        details = {**details, "draft_gen_id": str(gen.id)}
        run.details = details
        db.commit()

    if not details.get("draft_text"):
        text = _finish_article_generation(db, gen, model)
        details = {**details, "draft_text": text}
        run.details = details
        db.commit()

    run.generation_id = gen.id  # the final artifact of the pipeline
    run.step = "promote"
    db.commit()


def _step_promote(db: Session, run: OrchestratorRun) -> None:
    details = dict(run.details or {})
    run.status = OrchestratorRunStatus.PROMOTING
    run.step = "promote"
    db.commit()

    if run.content_piece_id is None:
        article = details["article"]
        cp = ContentPiece(
            id=uuid4(),
            tenant_id=run.tenant_id,
            owner_id=run.user_id,
            title=run.title or article.get("topic") or _title_from_brief(run.brief),
            body=details.get("draft_text") or "",
            format="blog_post",
            status=ContentStatus.DRAFT,
            source_generation_id=(
                UUID(details["draft_gen_id"]) if details.get("draft_gen_id") else None
            ),
            metadata_json=article_content_metadata(None, article),
        )
        db.add(cp)
        db.commit()
        run.content_piece_id = cp.id
        db.commit()

    run.step = "publish"
    db.commit()


def _step_publish(db: Session, run: OrchestratorRun) -> None:
    """Guarded publish: never bypass the editorial approval matrix (design C, D6)."""
    if not run.publish_channel:
        return
    details = dict(run.details or {})
    cp = db.get(ContentPiece, run.content_piece_id)
    if cp is None:
        raise PublisherError("content piece missing for the publish step")
    if cp.status == ContentStatus.PUBLISHED:
        return  # resume after a partial run — nothing to do

    if details.get("auto_approve") and cp.status == ContentStatus.DRAFT:
        # Unattended mode: drive the normal matrix explicitly and audit it.
        approvals = []
        for s in (ContentStatus.IN_REVIEW, ContentStatus.APPROVED):
            cp.status = s
            approvals.append(s.value)
        details = {**details, "approvals": approvals}
        run.details = details
        db.commit()

    if cp.status != ContentStatus.APPROVED:
        details = {**details, "publish_note": "skipped: content not approved"}
        run.details = details
        db.commit()
        return

    run.step = "publish"
    db.commit()
    channel = run.publish_channel.upper()
    result = _publish(channel, cp.title, cp.body, run.publish_config or {})
    cp.status = ContentStatus.PUBLISHED
    db.add(
        Publication(
            id=uuid4(),
            tenant_id=run.tenant_id,
            owner_id=run.user_id,
            content_piece_id=cp.id,
            channel=PublicationChannel(channel),
            status=PublicationStatus.PUBLISHED,
            url=result.get("url"),
            external_ref=result.get("external_ref"),
            target={"channel": channel},
        )
    )
    db.commit()


# -----------------------------------------------------------------------------
# Entry point
# -----------------------------------------------------------------------------
def execute_run(db: Session, run_id: UUID | str) -> str:
    """Drive one orchestrator run forward. Step-dispatch + per-step commits;
    safe to re-enter (Celery retry, /resume) at any point."""
    run = db.get(
        OrchestratorRun, run_id if isinstance(run_id, UUID) else UUID(str(run_id))
    )
    if not run:
        return "missing"

    if not (run.details or {}).get("article"):
        return _execute_legacy_run(db, run)

    try:
        if run.step in (None, "outline"):
            _step_outline(db, run)
        if run.step == "await_outline":
            return "awaiting-outline-approval"
        if run.step == "draft":
            _step_draft(db, run)
        if run.step == "promote":
            _step_promote(db, run)
        if run.step == "publish":
            _step_publish(db, run)

        run.status = OrchestratorRunStatus.COMPLETE
        run.step = "done"
        db.commit()
        return "ok"
    except Exception as e:
        run.status = OrchestratorRunStatus.FAILED
        run.error_message = f"{e.__class__.__name__}: {e}"[:500]
        db.commit()
        raise


def _execute_legacy_run(db: Session, run: OrchestratorRun) -> str:
    """The pre-design-C generic-copy pipeline (generate → promote → publish)."""
    model = run.model or settings.DEFAULT_LLM_MODEL
    try:
        run.status = OrchestratorRunStatus.GENERATING
        run.step = "generate"
        db.commit()

        gen = Generation(
            id=uuid4(),
            tenant_id=run.tenant_id,
            owner_id=run.user_id,
            brief=run.brief,
            status=GenerationStatus.QUEUED,
            metadata_json={"model": model, "orchestrator_run_id": str(run.id)},
        )
        db.add(gen)
        db.commit()
        run.generation_id = gen.id
        db.commit()

        text = _generate_text(run.brief, model)
        gen.result = text
        gen.status = GenerationStatus.COMPLETE
        db.commit()

        run.status = OrchestratorRunStatus.PROMOTING
        run.step = "promote"
        db.commit()

        cp = ContentPiece(
            id=uuid4(),
            tenant_id=run.tenant_id,
            owner_id=run.user_id,
            title=run.title or _title_from_brief(run.brief),
            body=text,
            status=ContentStatus.DRAFT,
            source_generation_id=gen.id,
        )
        db.add(cp)
        db.commit()
        run.content_piece_id = cp.id
        db.commit()

        # Optional auto-publish (opt-in): approve + publish via the adapter.
        if run.publish_channel:
            run.step = "publish"
            db.commit()
            channel = run.publish_channel.upper()
            result = _publish(channel, cp.title, text, run.publish_config or {})
            cp.status = ContentStatus.PUBLISHED
            db.add(
                Publication(
                    id=uuid4(),
                    tenant_id=run.tenant_id,
                    owner_id=run.user_id,
                    content_piece_id=cp.id,
                    channel=PublicationChannel(channel),
                    status=PublicationStatus.PUBLISHED,
                    url=result.get("url"),
                    external_ref=result.get("external_ref"),
                    target={"channel": channel},
                )
            )
            db.commit()

        run.status = OrchestratorRunStatus.COMPLETE
        run.step = "done"
        db.commit()
        return "ok"
    except Exception as e:
        run.status = OrchestratorRunStatus.FAILED
        run.error_message = f"{e.__class__.__name__}: {e}"[:500]
        db.commit()
        raise
