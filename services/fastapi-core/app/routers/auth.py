import re
from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.audit import record_audit_event
from app.core.authz import authz_client
from app.core.auth import (
    get_current_user,
    hash_password,
    issue_access,
    issue_refresh,
    verify_password,
)
from app.database import get_db
from app.models.tenant import Tenant
from app.models.user import User
from app.schemas.auth import Me, SignupRequest, TokenPair

router = APIRouter()

# Self-service signup is a hosted-only concern: in lite mode a workspace is
# created once via `make seed`, not by anonymous strangers hitting a public
# endpoint on someone's self-hosted instance. Registering the route only
# when not lite gets a real 404 in lite mode (not just a 403/503) — matches
# the existing test_register_is_not_in_public_core expectation.
_signup_router = router if not settings.is_lite else APIRouter()

_SLUG_STRIP = re.compile(r"[^a-z0-9]+")


def _slugify(name: str) -> str:
    slug = _SLUG_STRIP.sub("-", name.lower()).strip("-")
    return slug or "workspace"


async def _unique_slug(db: AsyncSession, base: str) -> str:
    """base, then base-2, base-3, ... until one isn't taken. Collisions are
    rare enough in practice that a bounded retry loop (not a single query)
    is fine — avoids a more complex "reserve and roll back" scheme."""
    candidate = base
    suffix = 1
    while True:
        existing = await db.scalar(select(Tenant).where(Tenant.slug == candidate))
        if existing is None:
            return candidate
        suffix += 1
        candidate = f"{base}-{suffix}"


@_signup_router.post(
    "/signup", response_model=TokenPair, status_code=status.HTTP_201_CREATED
)
async def signup(
    payload: SignupRequest,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Create a new tenant + its first user (admin). Self-service — no
    invite required, this is how a brand-new customer gets a workspace at
    all (there was previously no way to create one outside `make seed`)."""
    existing = await db.scalar(select(User).where(User.email == payload.email))
    if existing is not None:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "An account with this email already exists"
        )

    slug = await _unique_slug(db, _slugify(payload.tenant_name))
    tenant = Tenant(id=uuid4(), slug=slug, name=payload.tenant_name)
    db.add(tenant)
    await db.commit()
    await db.refresh(tenant)

    user = User(
        id=uuid4(),
        tenant_id=tenant.id,
        email=payload.email,
        password_hash=hash_password(payload.password),
        display_name=payload.display_name,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    # First user of a new tenant is its admin (billing, invites once those
    # exist) as well as a member (read/write access) — same two relations
    # scripts/seed.py grants the demo user.
    await authz_client.write_membership(str(user.id), str(tenant.id), role="admin")
    await authz_client.write_membership(str(user.id), str(tenant.id), role="member")

    ip = request.client.host if request.client else None
    ua = request.headers.get("user-agent")
    await record_audit_event(
        db,
        action="auth.signup",
        tenant_id=tenant.id,
        actor_user_id=user.id,
        actor_email=user.email,
        ip_address=ip,
        user_agent=ua,
        commit=True,
    )

    return TokenPair(
        access_token=issue_access(str(user.id), str(tenant.id)),
        refresh_token=issue_refresh(str(user.id), str(tenant.id)),
    )


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
