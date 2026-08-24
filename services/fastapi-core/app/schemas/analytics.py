from datetime import datetime

from pydantic import BaseModel, Field, field_validator


class TenantStripeCredentialUpsert(BaseModel):
    secret_key: str = Field(min_length=1)
    webhook_secret: str = Field(min_length=1)
    display_name: str | None = Field(default=None, max_length=120)

    @field_validator("secret_key", "webhook_secret", "display_name", mode="before")
    @classmethod
    def strip_strings(cls, value: str | None) -> str | None:
        if value is None or not isinstance(value, str):
            return value
        return value.strip() or None


class TenantStripeConfigOut(BaseModel):
    configured: bool
    secret_key_last4: str | None = None
    display_name: str | None = None
    webhook_url: str | None = None


class RevenueEventCreate(BaseModel):
    event_type: str
    content_piece_id: str | None = None
    event_count: int = Field(default=1, ge=1)
    amount_cents: int = Field(default=0, ge=0)
    currency: str = "USD"
    provider: str | None = None
    channel: str | None = None
    dedupe_key: str | None = None
    source_url: str | None = None
    occurred_at: datetime | None = None
    metadata: dict | None = None

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, value: str) -> str:
        value = value.strip().upper()
        if len(value) != 3 or not value.isalpha():
            raise ValueError("currency must be a 3-letter ISO code")
        return value

    @field_validator("event_type")
    @classmethod
    def normalize_event_type(cls, value: str) -> str:
        return value.strip().upper()


class RevenueEventOut(BaseModel):
    id: str
    event_type: str
    content_piece_id: str | None = None
    event_count: int
    amount_cents: int
    currency: str
    provider: str | None = None
    channel: str | None = None
    dedupe_key: str | None = None
    source_url: str | None = None
    occurred_at: datetime
    metadata: dict | None = None
    created_at: datetime


class AttributionSummaryOut(BaseModel):
    events: int
    visits: int
    signups: int
    leads: int
    customers: int
    revenue_cents: int
    currency: str = "USD"


class AttributionDeltaOut(BaseModel):
    absolute: int
    percent: int | None = None


class AttributionTrendOut(BaseModel):
    days: int
    current: AttributionSummaryOut
    previous: AttributionSummaryOut
    deltas: dict[str, AttributionDeltaOut]


class ChannelTrendOut(BaseModel):
    channel: str
    current: AttributionSummaryOut
    previous: AttributionSummaryOut
    deltas: dict[str, AttributionDeltaOut]


class SourceTrendOut(BaseModel):
    source_url: str
    current: AttributionSummaryOut
    previous: AttributionSummaryOut
    deltas: dict[str, AttributionDeltaOut]


class ContentTrendOut(BaseModel):
    content_piece_id: str
    title: str
    status: str
    current: AttributionSummaryOut
    previous: AttributionSummaryOut
    deltas: dict[str, AttributionDeltaOut]


class TrackingStatusOut(BaseModel):
    installed: bool
    events: int
    first_party_visits: int
    first_party_conversions: int
    last_seen_at: datetime | None = None


class ContentRecommendationOut(BaseModel):
    id: str
    kind: str
    content_piece_id: str | None = None
    title: str
    rationale: str
    score: float
    status: str
    orchestrator_run_id: str | None = None
    created_at: datetime


class ContentAttributionOut(AttributionSummaryOut):
    content_piece_id: str
    title: str
    status: str


class SourceAttributionOut(AttributionSummaryOut):
    source_url: str


class ChannelAttributionOut(AttributionSummaryOut):
    channel: str


class AnalyticsImportRow(BaseModel):
    content_piece_id: str | None = None
    source_url: str | None = None
    channel: str | None = None
    external_id: str | None = None
    visits: int = Field(default=0, ge=0)
    signups: int = Field(default=0, ge=0)
    leads: int = Field(default=0, ge=0)
    customers: int = Field(default=0, ge=0)
    revenue_cents: int = Field(default=0, ge=0)
    currency: str = "USD"
    occurred_at: datetime | None = None
    metadata: dict | None = None

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, value: str) -> str:
        return RevenueEventCreate.normalize_currency(value)


class AnalyticsImportRequest(BaseModel):
    provider: str = Field(pattern=r"^(ga4|gsc|manual)$")
    rows: list[AnalyticsImportRow] = Field(min_length=1, max_length=500)


class AnalyticsImportOut(BaseModel):
    imported_events: int
    imported_rows: int


class AnalyticsConnectorCreate(BaseModel):
    provider: str = Field(pattern=r"^(ga4|gsc)$")
    display_name: str = Field(min_length=1, max_length=200)
    external_property_id: str | None = None
    site_url: str | None = None
    metadata: dict | None = None


class AnalyticsConnectorOut(BaseModel):
    id: str
    provider: str
    status: str
    display_name: str
    external_property_id: str | None = None
    site_url: str | None = None
    scopes: list[str]
    last_sync_at: datetime | None = None
    last_sync_error: str | None = None
    metadata: dict | None = None
    created_at: datetime
    updated_at: datetime


class AnalyticsConnectorAuthUrlOut(BaseModel):
    configured: bool
    provider: str
    scopes: list[str]
    auth_url: str | None = None
    state: str | None = None
    message: str | None = None


class AnalyticsConnectorCallback(BaseModel):
    code: str = Field(min_length=1)
    state: str = Field(min_length=1)


class AnalyticsConnectorSyncOut(BaseModel):
    connector_id: str
    task_id: str | None = None
    status: str


class PublicTrackEvent(BaseModel):
    tenant_slug: str = Field(min_length=1, max_length=64)
    event_type: str = Field(pattern=r"^(signup|lead|customer|revenue)$")
    content_piece_id: str | None = None
    source_url: str | None = Field(default=None, max_length=600)
    external_id: str | None = Field(default=None, max_length=200)
    amount_cents: int = Field(default=0, ge=0)
    currency: str = "USD"
    metadata: dict | None = None

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, value: str) -> str:
        return RevenueEventCreate.normalize_currency(value)

    @field_validator("event_type")
    @classmethod
    def normalize_event_type(cls, value: str) -> str:
        return value.strip().upper()


class PublicTrackOut(BaseModel):
    ok: bool
    event_id: str
