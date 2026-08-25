"""Minimal MCP (Model Context Protocol) server over JSON-RPC 2.0.

Exposes OpenGrow as tools an AI agent (Claude Code, Cursor, …) can call
directly. Kept dependency-free (hand-rolled JSON-RPC over the existing /mcp HTTP
route), matching the repo's no-SDK ethos. Auth reuses the API-key / Bearer path
via get_current_user, so every call is tenant-scoped.
"""

from __future__ import annotations

import json
from uuid import uuid4

from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.authz import authz_client
from app.models.brand import Brand
from app.models.content_piece import ContentPiece, ContentStatus
from app.models.analytics import RevenueEvent
from app.models.generation import Generation
from app.models.orchestrator import OrchestratorRun
from app.models.publication import Publication
from app.models.user import User
from app.routers.content import _TRANSITIONS
from app.version import API_VERSION

MCP_PROTOCOL_VERSION = "2024-11-05"

TOOLS: list[dict] = [
    {
        "name": "list_content",
        "description": "List content pieces in the caller's workspace.",
        "inputSchema": {
            "type": "object",
            "properties": {"limit": {"type": "integer", "minimum": 1, "maximum": 100}},
        },
    },
    {
        "name": "create_content",
        "description": "Create a new draft content piece.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "body": {"type": "string"},
            },
            "required": ["title"],
        },
    },
    {
        "name": "get_attribution_summary",
        "description": "Return total attributed events and revenue (cents) for the workspace.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "list_brands",
        "description": "List brand profiles ('Brand DNA') in the caller's workspace.",
        "inputSchema": {
            "type": "object",
            "properties": {"limit": {"type": "integer", "minimum": 1, "maximum": 100}},
        },
    },
    {
        "name": "transition_content",
        "description": (
            "Move a content piece to a new editorial status "
            "(DRAFT, IN_REVIEW, APPROVED, PUBLISHED, ARCHIVED)."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "content_id": {"type": "string"},
                "status": {"type": "string"},
            },
            "required": ["content_id", "status"],
        },
    },
    {
        "name": "list_generations",
        "description": "List recent AI generations in the caller's workspace.",
        "inputSchema": {
            "type": "object",
            "properties": {"limit": {"type": "integer", "minimum": 1, "maximum": 100}},
        },
    },
    {
        "name": "get_generation",
        "description": "Get one generation's status and result text.",
        "inputSchema": {
            "type": "object",
            "properties": {"generation_id": {"type": "string"}},
            "required": ["generation_id"],
        },
    },
    {
        "name": "create_generation",
        "description": (
            "Start a new AI generation from a brief. Runs async — the returned "
            "generation is QUEUED; poll get_generation for the result. On a "
            "paid plan this holds credit up front for the estimated cost."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "brief": {"type": "string"},
                "model": {
                    "type": "string",
                    "description": "LiteLLM model string; falls back to the workspace default.",
                },
            },
            "required": ["brief"],
        },
    },
    {
        "name": "list_orchestrator_runs",
        "description": (
            "List recent orchestrator runs (multi-step generate -> promote -> "
            "publish pipelines) in the caller's workspace."
        ),
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "get_orchestrator_run",
        "description": "Get one orchestrator run's status, step, and result.",
        "inputSchema": {
            "type": "object",
            "properties": {"run_id": {"type": "string"}},
            "required": ["run_id"],
        },
    },
    {
        "name": "create_orchestrator_run",
        "description": (
            "Start a new orchestrator run: generate from a brief, promote to a "
            "draft content piece, and optionally auto-publish. Runs async — poll "
            "get_orchestrator_run for progress. For the article pipeline "
            "(outline -> approval -> draft), use the REST API directly."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "brief": {"type": "string"},
                "model": {"type": "string"},
                "title": {"type": "string"},
            },
            "required": ["brief"],
        },
    },
    {
        "name": "list_publications",
        "description": "List recent content-publishing attempts and their status.",
        "inputSchema": {
            "type": "object",
            "properties": {"limit": {"type": "integer", "minimum": 1, "maximum": 100}},
        },
    },
    {
        "name": "list_analytics_connectors",
        "description": (
            "List the workspace's analytics connectors (GA4, GSC, Stripe) "
            "and their connection status. OAuth connect flows must be "
            "completed in the app UI; this tool is read-only plus sync."
        ),
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "sync_analytics_connector",
        "description": (
            "Queue an on-demand sync for an already-connected analytics "
            "connector. The connector must be CONNECTED (finish OAuth in "
            "the app UI first) — returns a task id, does not wait for "
            "completion."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {"connector_id": {"type": "string"}},
            "required": ["connector_id"],
        },
    },
    {
        "name": "list_recommendations",
        "description": (
            "List content recommendations (REFRESH for decaying published "
            "content, DOUBLE_DOWN for growing content) computed daily from "
            "real trend data. Defaults to PENDING; pass status to filter."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "status": {
                    "type": "string",
                    "description": "PENDING, DISMISSED, or ACTIONED. Defaults to PENDING.",
                }
            },
        },
    },
    {
        "name": "dismiss_recommendation",
        "description": "Dismiss a pending content recommendation without acting on it.",
        "inputSchema": {
            "type": "object",
            "properties": {"recommendation_id": {"type": "string"}},
            "required": ["recommendation_id"],
        },
    },
    {
        "name": "start_run_from_recommendation",
        "description": (
            "Turn a pending recommendation directly into a new orchestrator "
            "run — the attribution loop's feedback step. Runs async, same "
            "as create_orchestrator_run."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {"recommendation_id": {"type": "string"}},
            "required": ["recommendation_id"],
        },
    },
]


async def _list_content(db: AsyncSession, user: User, args: dict) -> dict:
    limit = min(int(args.get("limit", 20) or 20), 100)
    row = await db.execute(
        select(ContentPiece)
        .where(
            ContentPiece.tenant_id == user.tenant_id,
            ContentPiece.is_deleted.is_(False),
        )
        .order_by(ContentPiece.updated_at.desc())
        .limit(limit)
    )
    return {
        "items": [
            {"id": str(cp.id), "title": cp.title, "status": cp.status.value}
            for cp in row.scalars().all()
        ]
    }


async def _create_content(db: AsyncSession, user: User, args: dict) -> dict:
    title = (args.get("title") or "").strip()
    if not title:
        raise ValueError("title is required")
    cp = ContentPiece(
        id=uuid4(),
        tenant_id=user.tenant_id,
        owner_id=user.id,
        title=title,
        body=args.get("body") or "",
        status=ContentStatus.DRAFT,
    )
    db.add(cp)
    await db.commit()
    await db.refresh(cp)
    return {"id": str(cp.id), "title": cp.title, "status": cp.status.value}


async def _attribution_summary(db: AsyncSession, user: User, args: dict) -> dict:
    events = await db.scalar(
        select(func.coalesce(func.sum(RevenueEvent.event_count), 0)).where(
            RevenueEvent.tenant_id == user.tenant_id,
            RevenueEvent.is_deleted.is_(False),
        )
    )
    revenue = await db.scalar(
        select(func.coalesce(func.sum(RevenueEvent.amount_cents), 0)).where(
            RevenueEvent.tenant_id == user.tenant_id,
            RevenueEvent.is_deleted.is_(False),
        )
    )
    return {"events": int(events or 0), "revenue_cents": int(revenue or 0)}


async def _list_brands(db: AsyncSession, user: User, args: dict) -> dict:
    limit = min(int(args.get("limit", 20) or 20), 100)
    row = await db.execute(
        select(Brand)
        .where(Brand.tenant_id == user.tenant_id, Brand.is_deleted.is_(False))
        .order_by(Brand.updated_at.desc())
        .limit(limit)
    )
    return {
        "items": [
            {"id": str(b.id), "name": b.name, "status": b.status.value}
            for b in row.scalars().all()
        ]
    }


async def _transition_content(db: AsyncSession, user: User, args: dict) -> dict:
    content_id = (args.get("content_id") or "").strip()
    status_value = (args.get("status") or "").strip()
    if not content_id or not status_value:
        raise ValueError("content_id and status are required")
    try:
        content_uuid = UUID(content_id)
    except ValueError:
        raise ValueError(f"Invalid content_id: {content_id}")
    try:
        target = ContentStatus(status_value)
    except ValueError:
        raise ValueError(f"Unknown status: {status_value}")

    if not await authz_client.check(
        str(user.id), "writer", f"content_piece:{content_uuid}"
    ):
        raise ValueError("Not permitted to transition this content piece")

    cp = await db.scalar(
        select(ContentPiece).where(
            ContentPiece.id == content_uuid,
            ContentPiece.tenant_id == user.tenant_id,
            ContentPiece.is_deleted.is_(False),
        )
    )
    if cp is None:
        raise ValueError(f"Content piece not found: {content_id}")
    if target != cp.status:
        if target not in _TRANSITIONS[cp.status]:
            raise ValueError(f"Illegal transition {cp.status.value} → {target.value}")
        cp.status = target
        await db.commit()
        await db.refresh(cp)
    return {"id": str(cp.id), "title": cp.title, "status": cp.status.value}


async def _list_generations(db: AsyncSession, user: User, args: dict) -> dict:
    limit = min(int(args.get("limit", 20) or 20), 100)
    row = await db.execute(
        select(Generation)
        .where(
            Generation.tenant_id == user.tenant_id,
            Generation.is_deleted.is_(False),
        )
        .order_by(Generation.created_at.desc())
        .limit(limit)
    )
    return {
        "items": [
            {"id": str(g.id), "brief": g.brief, "status": g.status.value}
            for g in row.scalars().all()
        ]
    }


async def _get_generation(db: AsyncSession, user: User, args: dict) -> dict:
    generation_id = (args.get("generation_id") or "").strip()
    if not generation_id:
        raise ValueError("generation_id is required")
    try:
        gen_uuid = UUID(generation_id)
    except ValueError:
        raise ValueError(f"Invalid generation_id: {generation_id}")

    if not await authz_client.check(str(user.id), "reader", f"generation:{gen_uuid}"):
        raise ValueError("Not permitted to view this generation")

    gen = await db.scalar(
        select(Generation).where(
            Generation.id == gen_uuid,
            Generation.tenant_id == user.tenant_id,
            Generation.is_deleted.is_(False),
        )
    )
    if gen is None:
        raise ValueError(f"Generation not found: {generation_id}")
    return {
        "id": str(gen.id),
        "brief": gen.brief,
        "status": gen.status.value,
        "result": gen.result,
        "error_message": gen.error_message,
    }


async def _create_generation(db: AsyncSession, user: User, args: dict) -> dict:
    # Reuses the real REST handler (authz, credit hold, task dispatch, usage
    # metering) rather than re-deriving that logic here — it's billing-
    # critical and has already had subtle bugs fixed in it twice.
    from app.routers.generations import create_generation
    from app.schemas.generation import GenerationCreate

    brief = (args.get("brief") or "").strip()
    if not brief:
        raise ValueError("brief is required")

    payload = GenerationCreate(brief=brief, model=args.get("model"))
    out = await create_generation(payload, user, db)
    return out.model_dump()


async def _list_orchestrator_runs(db: AsyncSession, user: User, args: dict) -> dict:
    row = await db.execute(
        select(OrchestratorRun)
        .where(
            OrchestratorRun.tenant_id == user.tenant_id,
            OrchestratorRun.is_deleted.is_(False),
        )
        .order_by(OrchestratorRun.created_at.desc())
        .limit(50)
    )
    return {
        "items": [
            {
                "run_id": str(r.id),
                "status": r.status.value,
                "step": r.step,
                "brief": r.brief,
            }
            for r in row.scalars().all()
        ]
    }


async def _get_orchestrator_run(db: AsyncSession, user: User, args: dict) -> dict:
    from app.routers.orchestrator import _get_tenant_run, _out

    run_id = (args.get("run_id") or "").strip()
    if not run_id:
        raise ValueError("run_id is required")
    try:
        run_uuid = UUID(run_id)
    except ValueError:
        raise ValueError(f"Invalid run_id: {run_id}")

    run = await _get_tenant_run(db, run_uuid, user.tenant_id)
    result = None
    if run.generation_id:
        gen = await db.get(Generation, run.generation_id)
        result = gen.result if gen else None
    return _out(run, result).model_dump()


async def _create_orchestrator_run(db: AsyncSession, user: User, args: dict) -> dict:
    # Reuses the real REST handler for the same reason as create_generation.
    from app.routers.orchestrator import create_run
    from app.schemas.orchestrator import OrchestratorRunCreate

    brief = (args.get("brief") or "").strip()
    if not brief:
        raise ValueError("brief is required")

    payload = OrchestratorRunCreate(
        brief=brief, model=args.get("model"), title=args.get("title")
    )
    out = await create_run(payload, user, db)
    return out.model_dump()


async def _list_publications(db: AsyncSession, user: User, args: dict) -> dict:
    limit = min(int(args.get("limit", 20) or 20), 100)
    row = await db.execute(
        select(Publication)
        .where(
            Publication.tenant_id == user.tenant_id,
            Publication.is_deleted.is_(False),
        )
        .order_by(Publication.created_at.desc())
        .limit(limit)
    )
    return {
        "items": [
            {
                "id": str(p.id),
                "content_piece_id": str(p.content_piece_id),
                "channel": p.channel.value,
                "status": p.status.value,
                "url": p.url,
            }
            for p in row.scalars().all()
        ]
    }


async def _list_analytics_connectors(db: AsyncSession, user: User, args: dict) -> dict:
    from app.routers.analytics import list_connectors

    connectors = await list_connectors(user, db)
    return {"items": [c.model_dump() for c in connectors]}


async def _sync_analytics_connector(db: AsyncSession, user: User, args: dict) -> dict:
    from app.routers.analytics import sync_connector

    connector_id = (args.get("connector_id") or "").strip()
    if not connector_id:
        raise ValueError("connector_id is required")
    try:
        connector_uuid = UUID(connector_id)
    except ValueError:
        raise ValueError(f"Invalid connector_id: {connector_id}")

    out = await sync_connector(connector_uuid, user, db)
    return out.model_dump()


async def _list_recommendations(db: AsyncSession, user: User, args: dict) -> dict:
    from app.routers.analytics import list_recommendations

    recs = await list_recommendations(
        user, db, status_filter=args.get("status", "PENDING")
    )
    return {"items": [r.model_dump() for r in recs]}


async def _dismiss_recommendation(db: AsyncSession, user: User, args: dict) -> dict:
    from app.routers.analytics import dismiss_recommendation

    rec_id = (args.get("recommendation_id") or "").strip()
    if not rec_id:
        raise ValueError("recommendation_id is required")
    try:
        rec_uuid = UUID(rec_id)
    except ValueError:
        raise ValueError(f"Invalid recommendation_id: {rec_id}")

    out = await dismiss_recommendation(rec_uuid, user, db)
    return out.model_dump()


async def _start_run_from_recommendation(
    db: AsyncSession, user: User, args: dict
) -> dict:
    from app.routers.analytics import start_run_from_recommendation

    rec_id = (args.get("recommendation_id") or "").strip()
    if not rec_id:
        raise ValueError("recommendation_id is required")
    try:
        rec_uuid = UUID(rec_id)
    except ValueError:
        raise ValueError(f"Invalid recommendation_id: {rec_id}")

    out = await start_run_from_recommendation(rec_uuid, user, db)
    return out.model_dump()


_HANDLERS = {
    "list_content": _list_content,
    "create_content": _create_content,
    "get_attribution_summary": _attribution_summary,
    "list_brands": _list_brands,
    "transition_content": _transition_content,
    "list_generations": _list_generations,
    "get_generation": _get_generation,
    "create_generation": _create_generation,
    "list_orchestrator_runs": _list_orchestrator_runs,
    "get_orchestrator_run": _get_orchestrator_run,
    "create_orchestrator_run": _create_orchestrator_run,
    "list_publications": _list_publications,
    "list_analytics_connectors": _list_analytics_connectors,
    "sync_analytics_connector": _sync_analytics_connector,
    "list_recommendations": _list_recommendations,
    "dismiss_recommendation": _dismiss_recommendation,
    "start_run_from_recommendation": _start_run_from_recommendation,
}


def _result(request_id, result) -> dict:
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def _error(request_id, code: int, message: str) -> dict:
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "error": {"code": code, "message": message},
    }


async def handle_jsonrpc(payload: dict, db: AsyncSession, user: User) -> dict | None:
    """Handle one JSON-RPC request. Returns None for notifications (no id)."""
    request_id = payload.get("id")
    method = payload.get("method")
    params = payload.get("params") or {}

    if request_id is None:
        return None  # notification — no response

    if method == "initialize":
        return _result(
            request_id,
            {
                "protocolVersion": MCP_PROTOCOL_VERSION,
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "opengrow", "version": API_VERSION},
            },
        )

    if method == "tools/list":
        return _result(request_id, {"tools": TOOLS})

    if method == "tools/call":
        name = params.get("name")
        args = params.get("arguments") or {}
        handler = _HANDLERS.get(name)
        if not handler:
            return _error(request_id, -32602, f"Unknown tool: {name}")
        try:
            data = await handler(db, user, args)
        except ValueError as e:
            return _result(
                request_id,
                {"content": [{"type": "text", "text": str(e)}], "isError": True},
            )
        except HTTPException as e:
            # create_generation/create_orchestrator_run reuse the real REST
            # handlers, which raise HTTPException for expected outcomes an
            # agent needs to handle inline (402 insufficient credits, 403
            # not permitted, 404 not found) — surface those as a JSON-RPC
            # tool error like ValueError, not an HTTP-transport failure.
            return _result(
                request_id,
                {
                    "content": [{"type": "text", "text": str(e.detail)}],
                    "isError": True,
                },
            )
        return _result(
            request_id,
            {
                "content": [{"type": "text", "text": json.dumps(data, default=str)}],
                "isError": False,
            },
        )

    return _error(request_id, -32601, f"Method not found: {method}")
