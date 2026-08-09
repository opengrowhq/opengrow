"""Shared brand + retrieval grounding for article generations.

Used by both the generation worker (`run_generation`) and the orchestrator's
article steps, so the two pipelines condition prompts identically. Grounding
is additive: any failure yields `(None, [])` and never fails the caller.
"""

from __future__ import annotations

import asyncio
import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.retrieval import retrieve_context_sync_db
from app.models.brand import Brand, BrandStatus

log = logging.getLogger(__name__)


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


def ground_article(
    db: Session, tenant_id, article: dict
) -> tuple[dict | None, list[dict]]:
    """Return (brand_profile, context_chunks) for an article brief.

    Picks the explicitly referenced brand (`article["brand_id"]`) or the most
    recently updated READY brand of the tenant, and retrieves asset context
    for the topic/keyword/audience query. Best-effort by design.
    """
    brand = None
    context: list[dict] = []
    try:
        q = select(Brand).where(
            Brand.tenant_id == tenant_id,
            Brand.is_deleted.is_(False),
            Brand.status == BrandStatus.READY,
        )
        if article.get("brand_id"):
            q = q.where(Brand.id == article["brand_id"])
        row = db.execute(q.order_by(Brand.updated_at.desc()).limit(1)).scalars().first()
        if row is not None:
            brand = row.profile
        query = " ".join(
            str(article.get(key) or "")
            for key in ("topic", "primary_keyword", "audience")
        ).strip()
        context = _run(retrieve_context_sync_db(db, str(tenant_id), query))
    except Exception as e:
        log.info("article grounding skipped: %s", e.__class__.__name__)
    return brand, context
