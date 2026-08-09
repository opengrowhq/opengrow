import enum
from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, Enum as SAEnum, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import TenantMixin


class AnalyticsConnectorProvider(str, enum.Enum):
    GA4 = "ga4"
    GSC = "gsc"


class AnalyticsConnectorStatus(str, enum.Enum):
    NEEDS_AUTH = "NEEDS_AUTH"
    CONNECTED = "CONNECTED"
    SYNCING = "SYNCING"
    DISCONNECTED = "DISCONNECTED"
    ERROR = "ERROR"


class AnalyticsConnector(TenantMixin, Base):
    """Tenant-scoped external analytics/search data source configuration."""

    __tablename__ = "analytics_connectors"

    owner_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    provider: Mapped[AnalyticsConnectorProvider] = mapped_column(
        SAEnum(
            AnalyticsConnectorProvider,
            name="analytics_connector_provider",
            values_callable=lambda enum_cls: [item.value for item in enum_cls],
        ),
        nullable=False,
        index=True,
    )
    status: Mapped[AnalyticsConnectorStatus] = mapped_column(
        SAEnum(AnalyticsConnectorStatus, name="analytics_connector_status"),
        nullable=False,
        default=AnalyticsConnectorStatus.NEEDS_AUTH,
        index=True,
    )
    display_name: Mapped[str] = mapped_column(String(200), nullable=False)
    external_property_id: Mapped[str | None] = mapped_column(String(200), nullable=True)
    site_url: Mapped[str | None] = mapped_column(String(600), nullable=True)
    scopes: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    last_sync_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_sync_error: Mapped[str | None] = mapped_column(String(500), nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
