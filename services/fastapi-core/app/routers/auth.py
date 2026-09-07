from typing import Annotated
from uuid import UUID

import jwt
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.audit import record_audit_event
from app.core.auth import (
    get_current_user,
    issue_access,
    issue_refresh,
    verify_password,
)
from app.database import get_db
from app.models.tenant import Tenant
from app.models.user import User
from app.schemas.auth import Me, RefreshRequest, TokenPair

router = APIRouter()


@router.post("/login", response_model=TokenPair)
async def login(
    request: Request,
    form: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    ip = request.client.host if request.client else None
    ua = request.headers.get("user-agent")

    row = await db.execute(
        select(User).where(User.email == form.username, User.is_active.is_(True))
    )
    user = row.scalar_one_or_none()
    if not user or not verify_password(form.password, user.password_hash):
        await record_audit_event(
            db,
            action="auth.login.failed",
            tenant_id=user.tenant_id if user else None,
            actor_email=form.username,
            ip_address=ip,
            user_agent=ua,
            commit=True,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials"
        )

    await record_audit_event(
        db,
        action="auth.login.success",
        tenant_id=user.tenant_id,
        actor_user_id=user.id,
        actor_email=user.email,
        ip_address=ip,
        user_agent=ua,
        commit=True,
    )
    return TokenPair(
        access_token=issue_access(str(user.id), str(user.tenant_id)),
        refresh_token=issue_refresh(str(user.id), str(user.tenant_id)),
    )


@router.post("/refresh", response_model=TokenPair)
async def refresh(
    body: RefreshRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Exchange a refresh token for a new token pair.

    The refresh token is rotated: alongside the new access token the client
    receives a NEW refresh token, and the presented one should be discarded —
    it is not tracked server-side, so rotation limits replay to the token's
    remaining lifetime only.
    """
    creds_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid refresh token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            body.refresh_token,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM],
        )
        if payload.get("kind") != "refresh":
            raise creds_exc
        user_id = payload.get("sub")
        tenant_id = payload.get("tid")
        if not user_id or not tenant_id:
            raise creds_exc
    except jwt.PyJWTError:
        raise creds_exc

    try:
        user_uuid = UUID(user_id)
    except (ValueError, AttributeError, TypeError):
        raise creds_exc

    row = await db.execute(select(User).where(User.id == user_uuid))
    user = row.scalar_one_or_none()
    if not user or not user.is_active:
        raise creds_exc
    if str(user.tenant_id) != tenant_id:
        raise creds_exc

    return TokenPair(
        access_token=issue_access(str(user.id), str(user.tenant_id)),
        refresh_token=issue_refresh(str(user.id), str(user.tenant_id)),
    )


@router.get("/me", response_model=Me)
async def me(
    current: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    tenant = await db.get(Tenant, current.tenant_id)
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found"
        )
    return Me(
        id=str(current.id),
        email=current.email,
        display_name=current.display_name,
        tenant_id=str(current.tenant_id),
        tenant_slug=tenant.slug,
    )
