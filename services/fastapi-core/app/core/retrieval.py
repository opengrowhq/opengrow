"""Retrieval of the tenant's own assets as grounding context for generation.

One interface, two backends — matching the repo's DEPLOYMENT_MODE invariant:
  production: Qdrant vector search (app.core.qdrant.search_assets)
  lite:       Postgres rows ranked by cosine similarity in Python (no extra service)

Retrieval is always additive: any failure returns [] so generation still runs.
"""

from __future__ import annotations

import logging
import math

from sqlalchemy import select

from app.config import settings
from app.core.litellm_client import embed
from app.models.asset import Asset, AssetStatus

log = logging.getLogger(__name__)


def cosine(a: list[float], b: list[float]) -> float:
    if not a or not b:
        return 0.0
    n = min(len(a), len(b))
    dot = sum(a[i] * b[i] for i in range(n))
    na = math.sqrt(sum(x * x for x in a[:n]))
    nb = math.sqrt(sum(x * x for x in b[:n]))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def rank_local_assets(rows, query_vec: list[float], k: int) -> list[dict]:
    """rows: iterable of (asset_id, filename, embedding) — embedding may be None."""
    scored = []
    for asset_id, filename, vector in rows:
        if not vector:
            continue
        scored.append(
            {
                "asset_id": str(asset_id),
                "filename": filename,
                "score": cosine(list(vector), query_vec),
            }
        )
    scored.sort(key=lambda r: r["score"], reverse=True)
    return scored[:k]


def _budget(hits: list[dict], char_budget: int) -> list[dict]:
    """Keep hits with a non-empty snippet, truncated to fit the char budget."""
    out, used = [], 0
    for hit in hits:
        snippet = (hit.get("snippet") or "").strip()
        if not snippet:
            continue
        room = char_budget - used
        if room <= 0:
            break
        hit["snippet"] = snippet[:room]
        used += len(hit["snippet"])
        out.append(hit)
    return out


def _normalize_qdrant_hits(raw: list[dict]) -> list[dict]:
    return [
        {
            "asset_id": (h.get("payload") or {}).get("asset_id") or h.get("id"),
            "filename": (h.get("payload") or {}).get("filename") or "asset",
            "snippet": (h.get("payload") or {}).get("text_snippet") or "",
            "score": h.get("score") or 0.0,
        }
        for h in raw
    ]


def _lite_hits(rows, query_vec: list[float], k: int) -> list[dict]:
    snippets = {str(r[0]): (r[3] or "") for r in rows}
    ranked = rank_local_assets([(r[0], r[1], r[2]) for r in rows], query_vec, k)
    return [{**r, "snippet": snippets.get(r["asset_id"], "")} for r in ranked]


async def retrieve_context(
    db, tenant_id: str, query: str, k: int = 3, char_budget: int = 6000
) -> list[dict]:
    if not query:
        return []
    try:
        query_vec = await embed(query)
    except Exception as e:  # no model pulled, no key, provider down
        log.info("retrieval skipped — embedding failed: %s", e.__class__.__name__)
        return []

    try:
        if settings.is_lite:
            rows = (
                await db.execute(
                    select(
                        Asset.id, Asset.filename, Asset.embedding, Asset.text_snippet
                    ).where(
                        Asset.tenant_id == tenant_id,
                        Asset.is_deleted.is_(False),
                        Asset.status == AssetStatus.INDEXED,
                    )
                )
            ).all()
            hits = _lite_hits(rows, query_vec, k)
        else:
            from app.core.qdrant import search_assets

            raw = await search_assets(tenant_id=tenant_id, vector=query_vec, top_k=k)
            hits = _normalize_qdrant_hits(raw)
    except Exception as e:
        log.info("retrieval skipped — search failed: %s", e.__class__.__name__)
        return []
    return _budget(hits, char_budget)


async def retrieve_context_sync_db(
    db, tenant_id: str, query: str, k: int = 3, char_budget: int = 6000
) -> list[dict]:
    """Same as retrieve_context but for Celery's sync Session (db.execute is sync)."""
    if not query:
        return []
    try:
        query_vec = await embed(query)
    except Exception as e:
        log.info("retrieval skipped — embedding failed: %s", e.__class__.__name__)
        return []
    try:
        if settings.is_lite:
            rows = db.execute(
                select(
                    Asset.id, Asset.filename, Asset.embedding, Asset.text_snippet
                ).where(
                    Asset.tenant_id == tenant_id,
                    Asset.is_deleted.is_(False),
                    Asset.status == AssetStatus.INDEXED,
                )
            ).all()
            hits = _lite_hits(rows, query_vec, k)
        else:
            from app.core.qdrant import search_assets

            raw = await search_assets(tenant_id=tenant_id, vector=query_vec, top_k=k)
            hits = _normalize_qdrant_hits(raw)
    except Exception as e:
        log.info("retrieval skipped — search failed: %s", e.__class__.__name__)
        return []
    return _budget(hits, char_budget)
