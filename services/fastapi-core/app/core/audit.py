"""Security audit trail — append-only, same-transaction writes.

record_audit_event() is called explicitly at each security-relevant call
site. It never catches its own exceptions: a failure here
must roll back whatever action it was recording, so the audit trail never
has a silent gap for an action that "succeeded."
"""

from __future__ import annotations

from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditLog


async def record_audit_event(
    db: AsyncSession,
    *,
    action: str,
    tenant_id: UUID | None = None,
    actor_user_id: UUID | None = None,
    actor_email: str | None = None,
    ref_type: str | None = None,
    ref_id: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
    details: dict | None = None,
    commit: bool = False,
) -> AuditLog:
    entry = AuditLog(
        id=uuid4(),
        tenant_id=tenant_id,
        actor_user_id=actor_user_id,
        actor_email=actor_email[:255] if actor_email else None,
        action=action,
        ref_type=ref_type,
        ref_id=ref_id,
        ip_address=ip_address[:64] if ip_address else None,
        user_agent=user_agent[:255] if user_agent else None,
        details=details,
    )
    db.add(entry)
    if commit:
        await db.commit()
        await db.refresh(entry)
    else:
        # Surface any constraint violation now, inside the caller's
        # transaction, rather than at their eventual commit far away.
        await db.flush()
    return entry
