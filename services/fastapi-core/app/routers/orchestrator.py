"""Orchestrator run endpoints — persisted content-cycle runs.

POST starts a run driven by the `run_orchestrator` Celery task; GET polls its
state. With an `article` brief the run follows the design-C pipeline (outline
→ optional AWAITING_OUTLINE_APPROVAL pause → draft → promote → guarded
publish); without one it keeps the legacy generate → promote behavior. The
pipeline logic lives in `app/core/orchestrator.py`.
"""

from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.core.usage import record_usage
from app.database import get_db
from app.models.generation import Generation
from app.models.orchestrator import OrchestratorRun, OrchestratorRunStatus
from app.models.user import User
from app.schemas.orchestrator import (
    OrchestratorRunCreate,
    OrchestratorRunOut,
    OutlineApproveIn,
)
from app.workers.tasks import run_orchestrator

router = APIRouter()


def _out(run: OrchestratorRun, result: str | None = None) -> OrchestratorRunOut:
    details = run.details or {}
    return OrchestratorRunOut(
        run_id=str(run.id),
        status=run.status.value,
        step=run.step,
        brief=run.brief,
        generation_id=str(run.generation_id) if run.generation_id else None,
        content_piece_id=str(run.content_piece_id) if run.content_piece_id else None,
        result=result,
        error_message=run.error_message,
        outline=details.get("sections"),
        outline_generation_id=details.get("outline_gen_id"),
        draft_generation_id=details.get("draft_gen_id"),
    )


async def _get_tenant_run(
    db: AsyncSession, run_id: UUID, tenant_id: UUID
) -> OrchestratorRun:
    row = await db.execute(
        select(OrchestratorRun).where(
            OrchestratorRun.id == run_id,
            OrchestratorRun.tenant_id == tenant_id,
            OrchestratorRun.is_deleted.is_(False),
        )
    )
    run = row.scalar_one_or_none()
    if not run:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Run not found")
    return run


@router.post(
    "/runs", response_model=OrchestratorRunOut, status_code=status.HTTP_202_ACCEPTED
)
async def create_run(
    payload: OrchestratorRunCreate,
    current: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    details = None
    brief = payload.brief
    if payload.article is not None:
        brief = brief or payload.article.topic
        details = {
            "article": payload.article.model_dump(),
            "pause_for_outline_approval": payload.pause_for_outline_approval,
            "auto_approve": payload.auto_approve,
        }
    run = OrchestratorRun(
        id=uuid4(),
        tenant_id=current.tenant_id,
        user_id=current.id,
        brief=brief,
        model=payload.model,
        title=payload.title,
        publish_channel=payload.publish_channel,
        publish_config=payload.publish_config,
        details=details,
    )
    db.add(run)
    await db.commit()
    await db.refresh(run)

    run_orchestrator.delay(str(run.id))

    await record_usage(
        db,
        tenant_id=current.tenant_id,
        user_id=current.id,
        kind="orchestrator_run",
        ref_type="orchestrator_run",
        ref_id=str(run.id),
    )
    return _out(run)


@router.get("/runs", response_model=list[OrchestratorRunOut])
async def list_runs(
    current: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    rows = await db.execute(
        select(OrchestratorRun)
        .where(
            OrchestratorRun.tenant_id == current.tenant_id,
            OrchestratorRun.is_deleted.is_(False),
        )
        .order_by(OrchestratorRun.created_at.desc())
        .limit(50)
    )
    return [_out(run) for run in rows.scalars().all()]


@router.get("/runs/{run_id}", response_model=OrchestratorRunOut)
async def get_run(
    run_id: UUID,
    current: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    run = await _get_tenant_run(db, run_id, current.tenant_id)

    result = None
    if run.generation_id:
        gen = await db.get(Generation, run.generation_id)
        result = gen.result if gen else None
    return _out(run, result)


@router.post("/runs/{run_id}/outline/approve", response_model=OrchestratorRunOut)
async def approve_outline(
    run_id: UUID,
    payload: OutlineApproveIn,
    current: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    run = await _get_tenant_run(db, run_id, current.tenant_id)
    if run.status != OrchestratorRunStatus.AWAITING_OUTLINE_APPROVAL:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"Run is not awaiting outline approval (status={run.status.value})",
        )

    run.details = {
        **(run.details or {}),
        "sections": [s.model_dump() for s in payload.outline],
    }
    run.status = OrchestratorRunStatus.QUEUED
    run.step = "draft"
    await db.commit()

    run_orchestrator.delay(str(run.id))
    return _out(run)


@router.post("/runs/{run_id}/resume", response_model=OrchestratorRunOut)
async def resume_run(
    run_id: UUID,
    current: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    run = await _get_tenant_run(db, run_id, current.tenant_id)
    if run.status != OrchestratorRunStatus.FAILED:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"Only FAILED runs can be resumed (status={run.status.value})",
        )

    run.status = OrchestratorRunStatus.QUEUED
    run.error_message = None
    await db.commit()

    run_orchestrator.delay(str(run.id))
    return _out(run)
