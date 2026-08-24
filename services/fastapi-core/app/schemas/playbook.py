from datetime import datetime

from pydantic import BaseModel, field_validator


class PlaybookCreate(BaseModel):
    kind: str
    name: str
    system_template: str

    @field_validator("system_template")
    @classmethod
    def _not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("system_template must not be blank")
        return v


class PlaybookOut(BaseModel):
    id: str
    kind: str
    name: str
    version: int
    system_template: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
