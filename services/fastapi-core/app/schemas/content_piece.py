from datetime import datetime

from pydantic import BaseModel, field_validator


class ContentPieceCreate(BaseModel):
    title: str
    body: str = ""
    format: str | None = None
    source_generation_id: str | None = None
    next_action: str | None = None
    due_at: datetime | None = None

    @field_validator("next_action")
    @classmethod
    def blank_next_action(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None


class ContentPieceFromGeneration(BaseModel):
    generation_id: str
    title: str | None = None  # defaults to a snippet of the brief if omitted
    next_action: str | None = None
    due_at: datetime | None = None


class ContentPieceUpdate(BaseModel):
    title: str | None = None
    body: str | None = None
    format: str | None = None
    next_action: str | None = None
    due_at: datetime | None = None

    @field_validator("next_action")
    @classmethod
    def blank_next_action(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None


class ContentPieceTransition(BaseModel):
    status: str  # target ContentStatus value


class ContentPieceOut(BaseModel):
    id: str
    title: str
    body: str
    format: str | None = None
    status: str
    source_generation_id: str | None = None
    next_action: str | None = None
    due_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
