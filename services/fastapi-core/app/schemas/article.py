from pydantic import BaseModel, Field, field_validator


class ArticleBrief(BaseModel):
    """Structured input for article generation (travels in Generation.metadata_json)."""

    topic: str = Field(min_length=1)
    primary_keyword: str = ""
    secondary_keywords: list[str] = Field(default_factory=list)
    audience: str = ""
    goal: str = "educate"  # educate | compare | convert
    tone: str = ""
    length_words: int = 1200
    sections_target: int = 5
    notes: str = ""
    slug: str = ""
    description: str = ""
    tags: list[str] = Field(default_factory=list)
    brand_id: str | None = None

    @field_validator(
        "topic",
        "primary_keyword",
        "audience",
        "tone",
        "notes",
        "slug",
        "description",
        "goal",
        mode="before",
    )
    @classmethod
    def _strip(cls, value):
        return value.strip() if isinstance(value, str) else value

    @field_validator("topic")
    @classmethod
    def _topic_not_blank(cls, value: str) -> str:
        if not value:
            raise ValueError("topic must not be blank")
        return value

    @field_validator("secondary_keywords", "tags", mode="before")
    @classmethod
    def _clean_list(cls, value):
        if value is None:
            return []
        if not isinstance(value, list):
            return value
        seen, out = set(), []
        for item in value:
            s = item.strip() if isinstance(item, str) else item
            if s and s not in seen:
                seen.add(s)
                out.append(s)
        return out
