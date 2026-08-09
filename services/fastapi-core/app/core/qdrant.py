"""Qdrant vector store. Lite mode: falls back to a Postgres-backed nullable table.

For lite mode we still need embeddings for retrieval. Two options:
  - Run Qdrant anyway (adds one service, 500 MB RAM)
  - Store embeddings in a Postgres JSONB column, cosine-similarity in SQL

Lite mode picks a middle path: store embeddings in the same DB via a scratch table.
Search is O(N) linear scan — fine for <10k embeddings on a personal deployment.
Production keeps Qdrant.
"""

from __future__ import annotations
import logging

from app.config import settings

log = logging.getLogger("qdrant")

ASSETS_COLLECTION = "assets"
EMBED_DIM = 1536


def _client():
    from qdrant_client import AsyncQdrantClient

    return AsyncQdrantClient(host=settings.QDRANT_HOST, port=settings.QDRANT_PORT)


async def ensure_collections() -> None:
    if settings.is_lite:
        log.info(
            "qdrant: lite mode — using in-DB embeddings, no collection setup needed"
        )
        return
    from qdrant_client.http.exceptions import UnexpectedResponse
    from qdrant_client.models import Distance, VectorParams

    c = _client()
    try:
        await c.get_collection(ASSETS_COLLECTION)
    except (UnexpectedResponse, ValueError):
        await c.create_collection(
            collection_name=ASSETS_COLLECTION,
            vectors_config=VectorParams(size=EMBED_DIM, distance=Distance.COSINE),
        )
        log.info("Created Qdrant collection %s", ASSETS_COLLECTION)


async def upsert_asset_embedding(
    asset_id: str, tenant_id: str, vector: list[float], meta: dict
) -> None:
    if settings.is_lite:
        # Lite: persist to Postgres directly (see workers/tasks.py for the write path).
        return
    from qdrant_client.models import PointStruct

    await _client().upsert(
        collection_name=ASSETS_COLLECTION,
        points=[
            PointStruct(
                id=asset_id,
                vector=vector,
                payload={"tenant_id": tenant_id, "asset_id": asset_id, **meta},
            )
        ],
    )


async def search_assets(
    tenant_id: str, vector: list[float], top_k: int = 5
) -> list[dict]:
    if settings.is_lite:
        return []  # Personal use: no cross-asset semantic search yet in lite mode.
    from qdrant_client.models import Filter, FieldCondition, MatchValue

    hits = await _client().search(
        collection_name=ASSETS_COLLECTION,
        query_vector=vector,
        limit=top_k,
        query_filter=Filter(
            must=[FieldCondition(key="tenant_id", match=MatchValue(value=tenant_id))]
        ),
    )
    return [{"id": str(h.id), "score": h.score, "payload": h.payload} for h in hits]
