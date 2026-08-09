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

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.authz import authz_client
from app.models.brand import Brand
from app.models.content_piece import ContentPiece, ContentStatus
from app.models.analytics import RevenueEvent
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


_HANDLERS = {
    "list_content": _list_content,
    "create_content": _create_content,
    "get_attribution_summary": _attribution_summary,
    "list_brands": _list_brands,
    "transition_content": _transition_content,
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
        return _result(
            request_id,
            {"content": [{"type": "text", "text": json.dumps(data)}], "isError": False},
        )

    return _error(request_id, -32601, f"Method not found: {method}")
