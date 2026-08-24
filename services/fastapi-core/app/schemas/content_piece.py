from datetime import datetime

from pydantic import BaseModel, field_validator


class ScheduledPublish(BaseModel):
    """A publish target to replay automatically once due_at passes and the
    piece is APPROVED — see app.workers.tasks.publish_due_content. config
    carries the same BYOK shape as a manual /publish call (site_url, api_key,
    …) since scheduled channels have no other credential source, mirroring
    the "BYOK, credentials come in the request config" convention every
    publisher adapter already follows."""

    channel: str
    config: dict = {}


class ContentPieceCreate(BaseModel):
    title: str
    body: str = ""
    format: str | None = None
    source_generation_id: str | None = None
    next_action: str | None = None
    due_at: datetime | None = None
    scheduled_publish: ScheduledPublish | None = None

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
    scheduled_publish: ScheduledPublish | None = None


class ContentPieceUpdate(BaseModel):
    title: str | None = None
    body: str | None = None
    format: str | None = None
    next_action: str | None = None
    due_at: datetime | None = None
    scheduled_publish: ScheduledPublish | None = None
    clear_scheduled_publish: bool = False

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
    scheduled_publish: ScheduledPublish | None = None
    created_at: datetime
    updated_at: datetime
