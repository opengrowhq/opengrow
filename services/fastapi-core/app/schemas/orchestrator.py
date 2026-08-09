from pydantic import BaseModel, Field, field_validator

from app.schemas.article import ArticleBrief


class OrchestratorRunCreate(BaseModel):
    brief: str
    model: str | None = None
    title: str | None = None
    # Opt-in auto-publish after the draft is created (BYOK creds in config).
    publish_channel: str | None = None
    publish_config: dict | None = None
    # Article pipeline (design C): when set, the run produces an article via
    # outline -> optional human pause -> draft -> promote -> guarded publish.
    article: ArticleBrief | None = None
    pause_for_outline_approval: bool = True
    auto_approve: bool = False


class OutlineSectionIn(BaseModel):
    heading: str = Field(min_length=1, max_length=300)
    points: list[str] = Field(default_factory=list)

    @field_validator("heading", mode="before")
    @classmethod
    def _strip(cls, value):
        return value.strip() if isinstance(value, str) else value


class OutlineApproveIn(BaseModel):
    """Approval = the (possibly edited) outline to draft from."""

    outline: list[OutlineSectionIn] = Field(min_length=1, max_length=15)


class OrchestratorRunOut(BaseModel):
    run_id: str
    status: str
    step: str | None = None
    brief: str | None = None
    generation_id: str | None = None
    content_piece_id: str | None = None
    result: str | None = None  # generated text, once the generate step completes
    error_message: str | None = None
    # Article pipeline fields (None for legacy runs).
    outline: list[dict] | None = None  # parsed sections while awaiting approval
    outline_generation_id: str | None = None
    draft_generation_id: str | None = None
