from datetime import datetime

from pydantic import BaseModel


class ApiKeyCreate(BaseModel):
    name: str = ""


class ApiKeyOut(BaseModel):
    id: str
    name: str
    prefix: str
    is_active: bool
    last_used_at: datetime | None = None
    created_at: datetime


class ApiKeyCreated(ApiKeyOut):
    # Plaintext secret — returned ONCE at creation, never again.
    key: str
