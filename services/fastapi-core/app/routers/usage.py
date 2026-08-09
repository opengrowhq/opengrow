from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.core.analytics_window import analytics_since
from app.core.pagination import Page, paginate, pagination
from app.database import get_db
from app.models.usage import UsageLedger
from app.models.user import User
from app.schemas.usage import UsageKindTotal, UsageLedgerOut, UsageSummaryOut

router = APIRouter()


def _out(e: UsageLedger) -> UsageLedgerOut:
    return UsageLedgerOut(
        id=str(e.id),
        kind=e.kind,
        units=e.units,
        cost_units=e.cost_units,
        ref_type=e.ref_type,
        ref_id=e.ref_id,
        created_at=e.created_at,
    )


@router.get("", response_model=list[UsageLedgerOut])
async def list_usage(
    current: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    response: Response,
    page: Annotated[Page, Depends(pagination)],
    kind: str | None = None,
    days: int | None = Query(default=None, ge=1, le=365),
):
    base = select(UsageLedger).where(
        UsageLedger.tenant_id == current.tenant_id,
        UsageLedger.is_deleted.is_(False),
    )
    if kind:
        base = base.where(UsageLedger.kind == kind)
    since = analytics_since(days)
    if since is not None:
        base = base.where(UsageLedger.created_at >= since)
    base = base.order_by(UsageLedger.created_at.desc())
    stmt = await paginate(db, base, page, response)
    row = await db.execute(stmt)
    return [_out(e) for e in row.scalars().all()]


@router.get("/summary", response_model=UsageSummaryOut)
async def usage_summary(
    current: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    days: int | None = Query(default=None, ge=1, le=365),
):
    conds = [
        UsageLedger.tenant_id == current.tenant_id,
        UsageLedger.is_deleted.is_(False),
    ]
    since = analytics_since(days)
    if since is not None:
        conds.append(UsageLedger.created_at >= since)

    row = await db.execute(
        select(
            UsageLedger.kind,
            func.coalesce(func.sum(UsageLedger.units), 0),
            func.coalesce(func.sum(UsageLedger.cost_units), 0),
            func.count(),
        )
        .where(*conds)
        .group_by(UsageLedger.kind)
    )
    by_kind = [
        UsageKindTotal(kind=k, units=int(u), cost_units=int(c), events=int(n))
        for k, u, c, n in row.all()
    ]
    return UsageSummaryOut(
        units=sum(x.units for x in by_kind),
        cost_units=sum(x.cost_units for x in by_kind),
        events=sum(x.events for x in by_kind),
        by_kind=by_kind,
    )
