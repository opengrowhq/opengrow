from pydantic import BaseModel


class GenerationCreate(BaseModel):
    brief: str
    reference_asset_id: str | None = None
    parent_generation_id: str | None = None  # e.g. draft → its outline generation
    model: str | None = None  # falls back to settings.DEFAULT_LLM_MODEL
    metadata: dict | None = None  # e.g. {"kind": "article_outline", "article": {...}}


class GenerationOut(BaseModel):
    id: str
    status: str
    brief: str
    result: str | None = None
    error_message: str | None = None
    task_id: str | None = None
    parent_generation_id: str | None = None
