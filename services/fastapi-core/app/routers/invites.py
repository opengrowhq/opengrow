"""Team-member invites: an admin invites an email address into their
tenant; the invitee accepts via a single-use link, creating their own
user account in that same tenant.

Reuses the OpenFGA admin/member relations already granted at signup
(app.routers.auth) — no new authz model needed, just the workflow to get
a second user into an existing tenant.
"""

from __future__ import annotations

import logging
import smtplib
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.auth import get_current_user, hash_password, issue_access, issue_refresh
from app.core.authz import authz_client
from app.database import get_db
from app.models.invite import Invite, InviteStatus, generate_invite_token
from app.models.tenant import Tenant
from app.models.user import User
from app.routers.billing import sync_seat_quantity
from app.schemas.auth import TokenPair
from app.schemas.invite import InviteAcceptRequest, InviteCreate, InviteOut, MemberOut

router = APIRouter()
log = logging.getLogger("invites")

_INVITE_TTL_DAYS = 7


async def _assert_tenant_admin(current: User) -> None:
    if not await authz_client.check(
        str(current.id), "admin", f"tenant:{current.tenant_id}"
    ):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, "Only a tenant admin can manage invites"
        )


def _send_invite_email(email: str, tenant_name: str, token: str) -> None:
    accept_url = f"{settings.FRONTEND_BASE_URL}/invites/{token}/accept"
    msg = EmailMessage()
    msg["From"] = "opengrow@opengrow.local"
    msg["To"] = email
    msg["Subject"] = f"You're invited to join {tenant_name} on OpenGrow"
    msg.set_content(
        f"You've been invited to join {tenant_name} on OpenGrow.\n\n"
        f"Accept your invite: {accept_url}\n\n"
        f"This link expires in {_INVITE_TTL_DAYS} days."
    )
    try:
        with smtplib.SMTP(
            settings.MAILPIT_HOST, settings.MAILPIT_SMTP_PORT, timeout=10
        ) as s:
            s.send_message(msg)
    except Exception as e:
        # Best-effort — the Invite row + token already exist; an admin can
        # always re-check /invites and the invitee can be given the link
        # out of band. Don't fail the whole request over a dev-mail hiccup.
        log.warning("invite email send failed: %s", e)


@router.post("", response_model=InviteOut, status_code=status.HTTP_201_CREATED)
async def create_invite(
    payload: InviteCreate,
    current: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    await _assert_tenant_admin(current)

    existing_user = await db.scalar(
        select(User).where(
            User.email == payload.email, User.tenant_id == current.tenant_id
        )
    )
    if existing_user is not None:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "This email is already a member of this workspace"
        )

    existing_invite = await db.scalar(
        select(Invite).where(
            Invite.tenant_id == current.tenant_id,
            Invite.email == payload.email,
            Invite.status == InviteStatus.PENDING,
        )
    )
    if existing_invite is not None:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "An invite is already pending for this email"
        )

    tenant = await db.get(Tenant, current.tenant_id)
    invite = Invite(
        id=uuid4(),
        tenant_id=current.tenant_id,
        email=payload.email,
        role=payload.role,
        token=generate_invite_token(),
        status=InviteStatus.PENDING,
        invited_by_user_id=current.id,
        expires_at=datetime.now(timezone.utc) + timedelta(days=_INVITE_TTL_DAYS),
    )
    db.add(invite)
    await db.commit()
    await db.refresh(invite)

    _send_invite_email(invite.email, tenant.name, invite.token)

    return InviteOut(
        id=str(invite.id),
        email=invite.email,
        role=invite.role,
        status=invite.status.value,
        expires_at=invite.expires_at,
    )


@router.get("", response_model=list[InviteOut])
async def list_invites(
    current: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    await _assert_tenant_admin(current)
    rows = await db.execute(
        select(Invite)
        .where(
            Invite.tenant_id == current.tenant_id,
            Invite.is_deleted.is_(False),
        )
        .order_by(Invite.created_at.desc())
    )
    return [
        InviteOut(
            id=str(i.id),
            email=i.email,
            role=i.role,
            status=i.status.value,
            expires_at=i.expires_at,
        )
        for i in rows.scalars().all()
    ]


@router.delete("/{invite_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_invite(
    invite_id: str,
    current: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    await _assert_tenant_admin(current)
    invite = await db.scalar(
        select(Invite).where(
            Invite.id == invite_id, Invite.tenant_id == current.tenant_id
        )
    )
    if invite is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Invite not found")
    if invite.status != InviteStatus.PENDING:
        raise HTTPException(
            status.HTTP_409_CONFLICT, f"Invite is already {invite.status.value.lower()}"
        )
    invite.status = InviteStatus.REVOKED
    await db.commit()


@router.get("/members", response_model=list[MemberOut])
async def list_members(
    current: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    rows = await db.execute(
        select(User)
        .where(User.tenant_id == current.tenant_id, User.is_active.is_(True))
        .order_by(User.email)
    )
    return [
        MemberOut(id=str(u.id), email=u.email, display_name=u.display_name)
        for u in rows.scalars().all()
    ]


@router.delete("/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_member(
    user_id: str,
    current: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Deactivate a tenant member (soft — flips is_active, matching the
    existing GET /members filter, rather than deleting the row and losing
    the audit trail / FK references)."""
    await _assert_tenant_admin(current)

    if user_id == str(current.id):
        raise HTTPException(
            status.HTTP_409_CONFLICT, "You can't remove yourself from the workspace"
        )

    target = await db.scalar(
        select(User).where(User.id == user_id, User.tenant_id == current.tenant_id)
    )
    if target is None or not target.is_active:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Member not found")

    if await authz_client.check(
        str(target.id), "admin", f"tenant:{current.tenant_id}"
    ):
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Can't remove an admin — transfer admin to another member first",
        )

    target.is_active = False
    await db.commit()

    member_count = await db.scalar(
        select(func.count(User.id)).where(
            User.tenant_id == current.tenant_id, User.is_active.is_(True)
        )
    )
    await sync_seat_quantity(db, current.tenant_id, member_count or 0)


@router.post("/{token}/accept", response_model=TokenPair)
async def accept_invite(
    token: str,
    payload: InviteAcceptRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """No auth required — the token itself is the credential proving the
    invitee is who the invite was sent to."""
    invite = await db.scalar(select(Invite).where(Invite.token == token))
    if invite is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Invite not found")
    if invite.status != InviteStatus.PENDING:
        raise HTTPException(
            status.HTTP_409_CONFLICT, f"Invite is already {invite.status.value.lower()}"
        )
    if invite.expires_at < datetime.now(timezone.utc):
        raise HTTPException(status.HTTP_410_GONE, "This invite has expired")

    existing = await db.scalar(select(User).where(User.email == invite.email))
    if existing is not None:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "An account with this email already exists"
        )

    user = User(
        id=uuid4(),
        tenant_id=invite.tenant_id,
        email=invite.email,
        password_hash=hash_password(payload.password),
        display_name=payload.display_name,
    )
    db.add(user)
    invite.status = InviteStatus.ACCEPTED
    await db.commit()
    await db.refresh(user)

    await authz_client.write_membership(
        str(user.id), str(invite.tenant_id), role=invite.role
    )
    # Every member (not just admins) needs the base "member" relation for
    # read/write access — an "admin" invite grants admin ON TOP of that,
    # not instead of it (mirrors app.routers.auth.signup granting both).
    if invite.role == "admin":
        await authz_client.write_membership(
            str(user.id), str(invite.tenant_id), role="member"
        )

    member_count = await db.scalar(
        select(func.count(User.id)).where(
            User.tenant_id == invite.tenant_id, User.is_active.is_(True)
        )
    )
    await sync_seat_quantity(db, invite.tenant_id, member_count or 0)

    return TokenPair(
        access_token=issue_access(str(user.id), str(invite.tenant_id)),
        refresh_token=issue_refresh(str(user.id), str(invite.tenant_id)),
    )
