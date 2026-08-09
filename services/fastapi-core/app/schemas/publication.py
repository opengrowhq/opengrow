from datetime import datetime

from pydantic import BaseModel, Field, field_validator


class PublishGitHubRequest(BaseModel):
    repo: str = Field(min_length=1, pattern=r"^[^/\s]+/[^/\s]+$")  # "owner/name"
    path: str | None = None  # default: content/<id>.md
    base_branch: str | None = None  # default: repo default branch
    branch: str | None = None  # default: opengrow/<id>
    commit_message: str | None = None
    pr_title: str | None = None
    pr_body: str | None = None
    draft: bool = False
    labels: list[str] = Field(default_factory=list)
    reviewers: list[str] = Field(default_factory=list)

    @field_validator("labels", "reviewers", mode="before")
    @classmethod
    def clean_str_list(cls, value: object) -> object:
        """Trim entries, drop blanks, de-dupe (order-preserving)."""
        if value is None:
            return []
        if not isinstance(value, list):
            return value
        seen: set[str] = set()
        out: list[str] = []
        for item in value:
            s = item.strip() if isinstance(item, str) else item
            if s and s not in seen:
                seen.add(s)
                out.append(s)
        return out

    @field_validator(
        "repo",
        "path",
        "base_branch",
        "branch",
        "commit_message",
        "pr_title",
        "pr_body",
        mode="before",
    )
    @classmethod
    def strip_blank_strings(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if not isinstance(value, str):
            return value
        stripped = value.strip()
        return stripped or None


class GitHubPublishConfigOut(BaseModel):
    configured: bool
    api_url: str
    source: str | None = None
    has_tenant_credential: bool = False
    token_last4: str | None = None
    display_name: str | None = None


class GitHubCredentialUpsert(BaseModel):
    token: str = Field(min_length=1)
    display_name: str | None = Field(default=None, max_length=120)

    @field_validator("token", "display_name", mode="before")
    @classmethod
    def strip_strings(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if not isinstance(value, str):
            return value
        stripped = value.strip()
        return stripped or None


class GitHubCredentialOut(BaseModel):
    configured: bool
    source: str
    token_last4: str
    display_name: str | None = None
    api_url: str


class PublishRequest(BaseModel):
    channel: str  # PublicationChannel value, e.g. "WORDPRESS", "GHOST"
    config: dict = Field(default_factory=dict)  # BYOK creds + channel options

    @field_validator("channel")
    @classmethod
    def upper(cls, v: str) -> str:
        return v.strip().upper()


class PublishChannelOut(BaseModel):
    channel: str
    implemented: bool


class PublicationOut(BaseModel):
    id: str
    content_piece_id: str
    channel: str
    status: str
    url: str | None = None
    external_ref: str | None = None
    error_message: str | None = None
    target: dict | None = None
    created_at: datetime
