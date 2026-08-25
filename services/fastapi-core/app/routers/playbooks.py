from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.core.authz import authz_client
from app.core.pagination import Page, paginate, pagination
from app.database import get_db
from app.models.playbook import Playbook, PlaybookKind
from app.models.user import User
from app.schemas.playbook import PlaybookCreate, PlaybookOut

router = APIRouter()

_VALID_KINDS = {k.value for k in PlaybookKind}


def _out(p: Playbook) -> PlaybookOut:
    return PlaybookOut(
        id=str(p.id),
        kind=p.kind.value,
        name=p.name,
        version=p.version,
        system_template=p.system_template,
        is_active=p.is_active,
        created_at=p.created_at,
        updated_at=p.updated_at,
    )


async def _assert_tenant_admin(current: User) -> None:
    if not await authz_client.check(
        str(current.id), "admin", f"tenant:{current.tenant_id}"
    ):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, "Only a tenant admin can manage playbooks"
        )


async def _load(db: AsyncSession, tenant_id: UUID, playbook_id: UUID) -> Playbook:
    row = await db.execute(
        select(Playbook).where(
            Playbook.id == playbook_id,
            Playbook.tenant_id == tenant_id,
            Playbook.is_deleted.is_(False),
        )
    )
    p = row.scalar_one_or_none()
    if not p:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Playbook not found")
    return p


@router.post("", response_model=PlaybookOut, status_code=status.HTTP_201_CREATED)
async def create_playbook(
    payload: PlaybookCreate,
    current: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    await _assert_tenant_admin(current)
    if payload.kind not in _VALID_KINDS:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"kind must be one of {sorted(_VALID_KINDS)}",
        )

    # New version = new row (history preserved); never edited in place.
    max_version = await db.execute(
        select(func.max(Playbook.version)).where(
            Playbook.tenant_id == current.tenant_id,
            Playbook.kind == payload.kind,
        )
    )
    next_version = (max_version.scalar_one_or_none() or 0) + 1

    playbook = Playbook(
        tenant_id=current.tenant_id,
        kind=PlaybookKind(payload.kind),
        name=payload.name,
        version=next_version,
        system_template=payload.system_template,
        is_active=False,
    )
    db.add(playbook)
    await db.commit()
    await db.refresh(playbook)
    return _out(playbook)


@router.get("", response_model=list[PlaybookOut])
async def list_playbooks(
    current: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    response: Response,
    page: Annotated[Page, Depends(pagination)],
    kind: str | None = None,
):
    base = select(Playbook).where(
        Playbook.tenant_id == current.tenant_id, Playbook.is_deleted.is_(False)
    )
    if kind is not None:
        base = base.where(Playbook.kind == kind)
    base = base.order_by(Playbook.kind, Playbook.version.desc())
    stmt = await paginate(db, base, page, response)
    row = await db.execute(stmt)
    return [_out(p) for p in row.scalars().all()]


@router.get("/{playbook_id}", response_model=PlaybookOut)
async def get_playbook(
    playbook_id: UUID,
    current: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return _out(await _load(db, current.tenant_id, playbook_id))


@router.post("/{playbook_id}/activate", response_model=PlaybookOut)
async def activate_playbook(
    playbook_id: UUID,
    current: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    await _assert_tenant_admin(current)
    playbook = await _load(db, current.tenant_id, playbook_id)

    # Deactivate any currently-active sibling of the same kind first — the
    # partial unique index (migration 026) forbids two active rows, and
    # flipping the old row off before the new one on avoids tripping it.
    current_active = (
        (
            await db.execute(
                select(Playbook).where(
                    Playbook.tenant_id == current.tenant_id,
                    Playbook.kind == playbook.kind,
                    Playbook.is_active.is_(True),
                    Playbook.is_deleted.is_(False),
                )
            )
        )
        .scalars()
        .all()
    )
    for row in current_active:
        row.is_active = False
    await db.flush()

    playbook.is_active = True
    await db.commit()
    await db.refresh(playbook)
    return _out(playbook)
