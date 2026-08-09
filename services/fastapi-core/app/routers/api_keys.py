from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.api_keys import generate_key
from app.core.audit import record_audit_event
from app.core.auth import get_current_user
from app.core.pagination import Page, paginate, pagination
from app.database import get_db
from app.models.api_key import ApiKey
from app.models.user import User
from app.schemas.api_key import ApiKeyCreate, ApiKeyCreated, ApiKeyOut

router = APIRouter()


def _out(k: ApiKey) -> ApiKeyOut:
    return ApiKeyOut(
        id=str(k.id),
        name=k.name,
        prefix=k.prefix,
        is_active=k.is_active,
        last_used_at=k.last_used_at,
        created_at=k.created_at,
    )


def _request_meta(request: Request) -> tuple[str | None, str | None]:
    ip = request.client.host if request.client else None
    return ip, request.headers.get("user-agent")


@router.post("", response_model=ApiKeyCreated, status_code=status.HTTP_201_CREATED)
async def create_api_key(
    payload: ApiKeyCreate,
    request: Request,
    current: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    token, prefix, key_hash = generate_key()
    key = ApiKey(
        id=uuid4(),
        tenant_id=current.tenant_id,
        user_id=current.id,
        name=payload.name.strip(),
        prefix=prefix,
        key_hash=key_hash,
    )
    db.add(key)
    ip, ua = _request_meta(request)
    await record_audit_event(
        db,
        action="api_key.created",
        tenant_id=current.tenant_id,
        actor_user_id=current.id,
        actor_email=current.email,
        ref_type="api_key",
        ref_id=str(key.id),
        ip_address=ip,
        user_agent=ua,
    )
    await db.commit()
    await db.refresh(key)
    out = _out(key).model_dump()
    return ApiKeyCreated(**out, key=token)


@router.get("", response_model=list[ApiKeyOut])
async def list_api_keys(
    current: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    response: Response,
    page: Annotated[Page, Depends(pagination)],
):
    base = (
        select(ApiKey)
        .where(ApiKey.tenant_id == current.tenant_id, ApiKey.is_deleted.is_(False))
        .order_by(ApiKey.created_at.desc())
    )
    stmt = await paginate(db, base, page, response)
    row = await db.execute(stmt)
    return [_out(k) for k in row.scalars().all()]


@router.delete("/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_api_key(
    key_id: UUID,
    request: Request,
    current: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    row = await db.execute(
        select(ApiKey).where(
            ApiKey.id == key_id,
            ApiKey.tenant_id == current.tenant_id,
            ApiKey.is_deleted.is_(False),
        )
    )
    key = row.scalar_one_or_none()
    if not key:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "API key not found")
    key.is_active = False
    key.is_deleted = True
    ip, ua = _request_meta(request)
    await record_audit_event(
        db,
        action="api_key.revoked",
        tenant_id=current.tenant_id,
        actor_user_id=current.id,
        actor_email=current.email,
        ref_type="api_key",
        ref_id=str(key.id),
        ip_address=ip,
        user_agent=ua,
    )
    await db.commit()
