from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.core.pagination import Page, paginate, pagination
from app.database import get_db
from app.models.audit import AuditLog
from app.models.user import User
from app.schemas.audit import AuditLogOut

router = APIRouter()


def _out(a: AuditLog) -> AuditLogOut:
    return AuditLogOut(
        id=str(a.id),
        created_at=a.created_at,
        tenant_id=str(a.tenant_id) if a.tenant_id else None,
        actor_user_id=str(a.actor_user_id) if a.actor_user_id else None,
        actor_email=a.actor_email,
        action=a.action,
        ref_type=a.ref_type,
        ref_id=a.ref_id,
        ip_address=a.ip_address,
        user_agent=a.user_agent,
        details=a.details,
    )


@router.get("", response_model=list[AuditLogOut])
async def list_audit_events(
    current: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    response: Response,
    page: Annotated[Page, Depends(pagination)],
    action: Annotated[str | None, Query()] = None,
    since: Annotated[datetime | None, Query()] = None,
    until: Annotated[datetime | None, Query()] = None,
):
    # tenant_id is never NULL here by construction — a null-tenant row (a
    # pre-auth failure with no resolvable tenant) can never equal any
    # authenticated caller's tenant_id, so it can never be returned.
    conditions = [AuditLog.tenant_id == current.tenant_id]
    if action:
        conditions.append(AuditLog.action == action)
    if since:
        conditions.append(AuditLog.created_at >= since)
    if until:
        conditions.append(AuditLog.created_at <= until)

    base = (
        select(AuditLog)
        .where(*conditions)
        .order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
    )
    stmt = await paginate(db, base, page, response)
    row = await db.execute(stmt)
    return [_out(a) for a in row.scalars().all()]
