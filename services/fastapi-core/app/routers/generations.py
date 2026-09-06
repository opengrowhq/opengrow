from typing import Annotated
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.auth import get_current_user
from app.core.authz import authz_client
from app.core.usage import record_usage
from app.database import get_db
from app.models.asset import Asset, AssetStatus
from app.models.generation import Generation, GenerationStatus
from app.models.user import User
from app.schemas.article import ArticleBrief
from app.schemas.generation import GenerationCreate, GenerationOut
from app.workers.tasks import run_generation

router = APIRouter()


@router.post("", response_model=GenerationOut, status_code=status.HTTP_202_ACCEPTED)
async def create_generation(
    payload: GenerationCreate,
    current: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    allowed = await authz_client.check(
        str(current.id), "writer", f"tenant:{current.tenant_id}"
    )
    if not allowed:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Not permitted to create generations for this tenant",
        )

    ref_id = None
    if payload.reference_asset_id:
        try:
            ref_id = UUID(payload.reference_asset_id)
        except ValueError:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST, "Invalid reference_asset_id"
            )
        asset_allowed = await authz_client.check(
            str(current.id), "reader", f"asset:{ref_id}"
        )
        if not asset_allowed:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN, "Not permitted to reference this asset"
            )
        row = await db.execute(
            select(Asset).where(
                Asset.id == ref_id, Asset.tenant_id == current.tenant_id
            )
        )
        asset = row.scalar_one_or_none()
        if not asset:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Reference asset not found")
        if asset.status != AssetStatus.INDEXED:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                f"Reference asset not ready (status={asset.status.value})",
            )

    parent_id = None
    parent_raw = payload.parent_generation_id
    meta = dict(payload.metadata or {})
    if not parent_raw and isinstance(meta.get("parent_generation_id"), str):
        # Backward compat: older clients send the parent inside metadata.
        parent_raw = meta.pop("parent_generation_id")
    if parent_raw:
        try:
            parent_id = UUID(parent_raw)
        except ValueError:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST, "Invalid parent_generation_id"
            )
        parent_allowed = await authz_client.check(
            str(current.id), "reader", f"generation:{parent_id}"
        )
        if not parent_allowed:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                "Not permitted to reference this generation",
            )
        row = await db.execute(
            select(Generation).where(
                Generation.id == parent_id,
                Generation.tenant_id == current.tenant_id,
                Generation.is_deleted.is_(False),
            )
        )
        if not row.scalar_one_or_none():
            raise HTTPException(
                status.HTTP_404_NOT_FOUND, "Parent generation not found"
            )

    if meta.get("kind") in ("article_outline", "article_draft") and isinstance(
        meta.get("article"), dict
    ):
        try:
            ArticleBrief(**meta["article"])
        except ValidationError as e:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_CONTENT,
                f"Invalid article brief: {e.errors()[0]['msg']}",
            ) from e

    model = payload.model or settings.DEFAULT_LLM_MODEL
    gen = Generation(
        tenant_id=current.tenant_id,
        owner_id=current.id,
        brief=payload.brief,
        reference_asset_id=ref_id,
        parent_generation_id=parent_id,
        status=GenerationStatus.QUEUED,
        metadata_json={**meta, "model": model},
    )

    db.add(gen)
    await db.commit()
    await db.refresh(gen)

    await authz_client.bind_resource_to_tenant(
        "generation", str(gen.id), str(current.tenant_id), str(current.id)
    )

    task = run_generation.delay(str(gen.id))
    gen.task_id = task.id
    await db.commit()

    # Meter the generation request (mechanism; enforcement is layered on top).
    await record_usage(
        db,
        tenant_id=current.tenant_id,
        user_id=current.id,
        kind="generation",
        units=1,
        ref_type="generation",
        ref_id=str(gen.id),
    )

    return GenerationOut(
        id=str(gen.id),
        status=gen.status.value,
        brief=gen.brief,
        result=None,
        error_message=None,
        task_id=gen.task_id,
        parent_generation_id=str(parent_id) if parent_id else None,
    )


@router.get("/{generation_id}", response_model=GenerationOut)
async def get_generation(
    generation_id: UUID,
    current: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    allowed = await authz_client.check(
        str(current.id), "reader", f"generation:{generation_id}"
    )
    if not allowed:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, "Not permitted to view this generation"
        )
    row = await db.execute(
        select(Generation).where(
            Generation.id == generation_id,
            Generation.tenant_id == current.tenant_id,
            Generation.is_deleted.is_(False),
        )
    )
    g = row.scalar_one_or_none()
    if not g:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Generation not found")
    return GenerationOut(
        id=str(g.id),
        status=g.status.value,
        brief=g.brief,
        result=g.result,
        error_message=g.error_message,
        task_id=g.task_id,
        parent_generation_id=str(g.parent_generation_id)
        if g.parent_generation_id
        else None,
    )


@router.get("/{generation_id}/children", response_model=list[GenerationOut])
async def list_generation_children(
    generation_id: UUID,
    current: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    allowed = await authz_client.check(
        str(current.id), "reader", f"generation:{generation_id}"
    )
    if not allowed:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, "Not permitted to view this generation"
        )
    rows = await db.execute(
        select(Generation)
        .where(
            Generation.parent_generation_id == generation_id,
            Generation.tenant_id == current.tenant_id,
            Generation.is_deleted.is_(False),
        )
        .order_by(Generation.created_at)
    )
    return [
        GenerationOut(
            id=str(g.id),
            status=g.status.value,
            brief=g.brief,
            result=g.result,
            error_message=g.error_message,
            task_id=g.task_id,
            parent_generation_id=str(g.parent_generation_id)
            if g.parent_generation_id
            else None,
        )
        for g in rows.scalars().all()
    ]
