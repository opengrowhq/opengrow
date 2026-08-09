from typing import Annotated
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.core.authz import authz_client
from app.core.minio_client import put_temp
from app.database import get_db
from app.models.asset import Asset, AssetStatus
from app.models.user import User
from app.schemas.asset import AssetOut, UploadResponse
from app.workers.tasks import scan_asset

router = APIRouter()

MAX_UPLOAD_BYTES = 25 * 1024 * 1024  # 25 MiB
ALLOWED_CT_PREFIXES = ("image/", "text/", "application/pdf", "application/json")


@router.post(
    "/upload", response_model=UploadResponse, status_code=status.HTTP_202_ACCEPTED
)
async def upload_asset(
    file: UploadFile,
    current: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    ct = file.content_type or "application/octet-stream"
    if not any(ct.startswith(p) for p in ALLOWED_CT_PREFIXES):
        raise HTTPException(
            status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, f"Unsupported content type: {ct}"
        )

    allowed = await authz_client.check(
        str(current.id), "writer", f"tenant:{current.tenant_id}"
    )
    if not allowed:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, "Not permitted to upload for this tenant"
        )

    data = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "File too large")

    from io import BytesIO
    from uuid import uuid4

    temp_key = f"{current.tenant_id}/{uuid4()}/{file.filename}"
    put_temp(temp_key, BytesIO(data), size=len(data), content_type=ct)

    asset = Asset(
        tenant_id=current.tenant_id,
        owner_id=current.id,
        filename=file.filename or "unnamed",
        content_type=ct,
        size_bytes=len(data),
        temp_object_key=temp_key,
        status=AssetStatus.UPLOADED,
    )
    db.add(asset)
    await db.commit()
    await db.refresh(asset)

    await authz_client.bind_resource_to_tenant(
        "asset", str(asset.id), str(current.tenant_id), str(current.id)
    )

    task = scan_asset.delay(str(asset.id))
    return UploadResponse(
        asset_id=str(asset.id), scan_job_id=task.id, status=asset.status.value
    )


@router.get("/{asset_id}", response_model=AssetOut)
async def get_asset(
    asset_id: UUID,
    current: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    allowed = await authz_client.check(str(current.id), "reader", f"asset:{asset_id}")
    if not allowed:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, "Not permitted to view this asset"
        )
    row = await db.execute(
        select(Asset).where(
            Asset.id == asset_id,
            Asset.tenant_id == current.tenant_id,
            Asset.is_deleted.is_(False),
        )
    )
    asset = row.scalar_one_or_none()
    if not asset:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Asset not found")
    return AssetOut(
        id=str(asset.id),
        filename=asset.filename,
        content_type=asset.content_type,
        size_bytes=asset.size_bytes,
        status=asset.status.value,
        scan_message=asset.scan_message,
    )
