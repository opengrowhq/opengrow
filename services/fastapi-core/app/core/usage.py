"""Usage metering helper — record billable actions into the UsageLedger."""

from __future__ import annotations

from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.usage import UsageLedger


async def record_usage(
    db: AsyncSession,
    *,
    tenant_id: UUID,
    kind: str,
    units: int = 1,
    cost_units: int = 0,
    ref_type: str | None = None,
    ref_id: str | None = None,
    user_id: UUID | None = None,
    details: dict | None = None,
    commit: bool = True,
) -> UsageLedger:
    entry = UsageLedger(
        id=uuid4(),
        tenant_id=tenant_id,
        user_id=user_id,
        kind=kind,
        units=units,
        cost_units=cost_units,
        ref_type=ref_type,
        ref_id=ref_id,
        details=details,
    )
    db.add(entry)
    if commit:
        await db.commit()
        await db.refresh(entry)
    return entry


def record_usage_sync(
    db,
    *,
    tenant_id: UUID,
    kind: str,
    units: int = 1,
    cost_units: int = 0,
    ref_type: str | None = None,
    ref_id: str | None = None,
    user_id: UUID | None = None,
    details: dict | None = None,
    commit: bool = True,
) -> UsageLedger:
    """Sync twin of record_usage for the Celery workers (plain Session)."""
    entry = UsageLedger(
        id=uuid4(),
        tenant_id=tenant_id,
        user_id=user_id,
        kind=kind,
        units=units,
        cost_units=cost_units,
        ref_type=ref_type,
        ref_id=ref_id,
        details=details,
    )
    db.add(entry)
    if commit:
        db.commit()
        db.refresh(entry)
    return entry
