"""Additive, non-breaking pagination for list endpoints.

List endpoints keep returning a plain JSON array (unchanged contract). Callers
opt in with `?limit=&offset=`; the total row count is returned in the
`X-Total-Count` response header. Omitting both params returns the full list
(capped only when a limit is supplied).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated

from fastapi import Query, Response
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import Select

MAX_LIMIT = 200


@dataclass
class Page:
    limit: int | None
    offset: int


def pagination(
    limit: Annotated[
        int | None,
        Query(ge=1, le=MAX_LIMIT, description="Max items to return; omit for all."),
    ] = None,
    offset: Annotated[int, Query(ge=0, description="Rows to skip.")] = 0,
) -> Page:
    return Page(limit=limit, offset=offset)


async def paginate(
    db: AsyncSession, base_stmt: Select, page: Page, response: Response
) -> Select:
    """Set X-Total-Count from the unpaginated query and return a sliced stmt."""
    total = await db.scalar(
        select(func.count()).select_from(base_stmt.order_by(None).subquery())
    )
    response.headers["X-Total-Count"] = str(total or 0)
    stmt = base_stmt
    if page.offset:
        stmt = stmt.offset(page.offset)
    if page.limit is not None:
        stmt = stmt.limit(page.limit)
    return stmt
