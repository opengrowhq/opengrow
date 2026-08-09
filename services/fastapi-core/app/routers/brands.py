from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.core.authz import authz_client
from app.core.brand_scraper import UnsafeURLError, validate_public_http_url
from app.core.pagination import Page, paginate, pagination
from app.database import get_db
from app.models.brand import Brand, BrandStatus
from app.models.user import User
from app.schemas.brand import BrandCreate, BrandOut, BrandUpdate
from app.workers.tasks import build_brand_profile

router = APIRouter()


def _out(b: Brand) -> BrandOut:
    return BrandOut(
        id=str(b.id),
        name=b.name,
        source_url=b.source_url,
        status=b.status.value,
        profile=b.profile,
        error_message=b.error_message,
        created_at=b.created_at,
        updated_at=b.updated_at,
    )


async def _load(db: AsyncSession, tenant_id: UUID, brand_id: UUID) -> Brand:
    row = await db.execute(
        select(Brand).where(
            Brand.id == brand_id,
            Brand.tenant_id == tenant_id,
            Brand.is_deleted.is_(False),
        )
    )
    b = row.scalar_one_or_none()
    if not b:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Brand not found")
    return b


@router.post("", response_model=BrandOut, status_code=status.HTTP_202_ACCEPTED)
async def create_brand(
    payload: BrandCreate,
    current: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    if not await authz_client.check(
        str(current.id), "writer", f"tenant:{current.tenant_id}"
    ):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not permitted for this tenant")

    # SSRF pre-check before we enqueue (the worker re-checks per redirect hop too).
    if payload.source_url:
        try:
            validate_public_http_url(payload.source_url)
        except UnsafeURLError as e:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Unsafe URL: {e}")

    brand = Brand(
        tenant_id=current.tenant_id,
        owner_id=current.id,
        name=payload.name,
        source_url=payload.source_url,
        status=BrandStatus.PENDING,
    )
    db.add(brand)
    await db.commit()
    await db.refresh(brand)

    await authz_client.bind_resource_to_tenant(
        "brand", str(brand.id), str(current.tenant_id), str(current.id)
    )

    if payload.source_url:
        build_brand_profile.delay(str(brand.id))
    else:
        brand.status = BrandStatus.READY
        brand.profile = {}
        await db.commit()
        await db.refresh(brand)

    return _out(brand)


@router.get("", response_model=list[BrandOut])
async def list_brands(
    current: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    response: Response,
    page: Annotated[Page, Depends(pagination)],
):
    base = (
        select(Brand)
        .where(Brand.tenant_id == current.tenant_id, Brand.is_deleted.is_(False))
        .order_by(Brand.updated_at.desc())
    )
    stmt = await paginate(db, base, page, response)
    row = await db.execute(stmt)
    return [_out(b) for b in row.scalars().all()]


@router.get("/{brand_id}", response_model=BrandOut)
async def get_brand(
    brand_id: UUID,
    current: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    if not await authz_client.check(str(current.id), "reader", f"brand:{brand_id}"):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not permitted")
    return _out(await _load(db, current.tenant_id, brand_id))


@router.patch("/{brand_id}", response_model=BrandOut)
async def update_brand(
    brand_id: UUID,
    payload: BrandUpdate,
    current: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    if not await authz_client.check(str(current.id), "writer", f"brand:{brand_id}"):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not permitted")
    b = await _load(db, current.tenant_id, brand_id)
    if payload.name is not None:
        b.name = payload.name
    if payload.profile is not None:
        b.profile = payload.profile
    await db.commit()
    await db.refresh(b)
    return _out(b)
