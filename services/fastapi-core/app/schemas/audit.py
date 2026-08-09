from datetime import datetime

from pydantic import BaseModel


class AuditLogOut(BaseModel):
    id: str
    created_at: datetime
    tenant_id: str | None = None
    actor_user_id: str | None = None
    actor_email: str | None = None
    action: str
    ref_type: str | None = None
    ref_id: str | None = None
    ip_address: str | None = None
    user_agent: str | None = None
    details: dict | None = None
