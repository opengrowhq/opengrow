import csv
import io
from datetime import datetime, timezone
from typing import Annotated
from uuid import UUID, uuid4

import stripe
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    Request,
    Response,
    UploadFile,
    status,
)
from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.core.analytics_import import event_dedupe_key, normalize_channel
from app.core.pagination import Page, paginate, pagination
from app.core.analytics_window import analytics_periods, analytics_since, trend_delta
from app.core.authz import authz_client
from app.core.oauth_state import consume_oauth_state, issue_oauth_state
from app.core.google_oauth import (
    GoogleOAuthError,
    build_google_auth_url,
    exchange_google_oauth_code,
    google_scopes,
)
from app.config import settings
from app.database import get_db
from app.models.analytics import RevenueEvent, RevenueEventType
from app.models.analytics_connector import (
    AnalyticsConnector,
    AnalyticsConnectorProvider,
    AnalyticsConnectorStatus,
)
from app.core.audit import record_audit_event
from app.core.credential_crypto import (
    CredentialCryptoError,
    decrypt_secret,
    encrypt_secret,
)
from app.models.content_piece import ContentPiece
from app.models.content_recommendation import (
    ContentRecommendation,
    ContentRecommendationStatus,
)
from app.models.tenant import Tenant
from app.models.tenant_stripe import TenantStripeCredential, TenantStripeWebhookEvent
from app.models.user import User
from app.schemas.analytics import (
    AnalyticsConnectorAuthUrlOut,
    AnalyticsConnectorCallback,
    AnalyticsConnectorCreate,
    AnalyticsConnectorOut,
    AnalyticsConnectorSyncOut,
    AnalyticsImportOut,
    AnalyticsImportRequest,
    AnalyticsImportRow,
    AttributionDeltaOut,
    AttributionSummaryOut,
    AttributionTrendOut,
    ChannelTrendOut,
    ChannelAttributionOut,
    ContentAttributionOut,
    ContentRecommendationOut,
    ContentTrendOut,
    PublicTrackEvent,
    PublicTrackOut,
    RevenueEventCreate,
    RevenueEventOut,
    SourceAttributionOut,
    SourceTrendOut,
    TenantStripeConfigOut,
    TenantStripeCredentialUpsert,
    TrackingStatusOut,
)
from app.workers.tasks import sync_analytics_connector

router = APIRouter()

CSV_CONTENT_TYPES = {"text/csv", "application/vnd.ms-excel", "text/plain"}
MAX_IMPORT_CSV_BYTES = 2 * 1024 * 1024  # 2 MiB
MAX_IMPORT_CSV_ROWS = 500  # matches AnalyticsImportRequest.rows max_length
CSV_IMPORT_COLUMNS = {
    "content_piece_id",
    "source_url",
    "channel",
    "external_id",
    "visits",
    "signups",
    "leads",
    "customers",
    "revenue_cents",
    "currency",
    "occurred_at",
}


def _csv_row_to_import_row(raw: dict[str, str | None]) -> AnalyticsImportRow:
    cleaned: dict[str, object] = {}
    for key in ("content_piece_id", "source_url", "channel", "external_id", "currency"):
        value = (raw.get(key) or "").strip()
        if value:
            cleaned[key] = value
    for key in ("visits", "signups", "leads", "customers", "revenue_cents"):
        value = (raw.get(key) or "").strip()
        if value:
            cleaned[key] = int(value)
    occurred_at = (raw.get("occurred_at") or "").strip()
    if occurred_at:
        cleaned["occurred_at"] = occurred_at
    return AnalyticsImportRow.model_validate(cleaned)


PIXEL_GIF = (
    b"GIF89a\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00\xff\xff\xff!"
    b"\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00"
    b"\x00\x02\x02D\x01\x00;"
)


def _empty_counts() -> dict[str, int]:
    return {
        "events": 0,
        "visits": 0,
        "signups": 0,
        "leads": 0,
        "customers": 0,
        "revenue_cents": 0,
    }


def _apply_event(counts: dict[str, int], event: RevenueEvent) -> None:
    event_count = event.event_count or 1
    counts["events"] += event_count
    if event.event_type == RevenueEventType.VISIT:
        counts["visits"] += event_count
    elif event.event_type == RevenueEventType.SIGNUP:
        counts["signups"] += event_count
    elif event.event_type == RevenueEventType.LEAD:
        counts["leads"] += event_count
    elif event.event_type == RevenueEventType.CUSTOMER:
        counts["customers"] += event_count
    elif event.event_type == RevenueEventType.REVENUE:
        counts["revenue_cents"] += event.amount_cents


def _out(event: RevenueEvent) -> RevenueEventOut:
    return RevenueEventOut(
        id=str(event.id),
        event_type=event.event_type.value,
        content_piece_id=str(event.content_piece_id)
        if event.content_piece_id
        else None,
        event_count=event.event_count,
        amount_cents=event.amount_cents,
        currency=event.currency,
        provider=event.provider,
        channel=event.channel,
        dedupe_key=event.dedupe_key,
        source_url=event.source_url,
        occurred_at=event.occurred_at,
        metadata=event.metadata_json,
        created_at=event.created_at,
    )


def _connector_out(connector: AnalyticsConnector) -> AnalyticsConnectorOut:
    metadata = dict(connector.metadata_json or {})
    if metadata.get("oauth"):
        metadata["oauth"] = {"connected": True}
    return AnalyticsConnectorOut(
        id=str(connector.id),
        provider=connector.provider.value,
        status=connector.status.value,
        display_name=connector.display_name,
        external_property_id=connector.external_property_id,
        site_url=connector.site_url,
        scopes=connector.scopes or [],
        last_sync_at=connector.last_sync_at,
        last_sync_error=connector.last_sync_error,
        metadata=metadata or None,
        created_at=connector.created_at,
        updated_at=connector.updated_at,
    )


def _apply_since(stmt, since: datetime | None):
    if since is None:
        return stmt
    return stmt.where(RevenueEvent.occurred_at >= since)


def _apply_period(stmt, start: datetime | None, end: datetime | None):
    if start is not None:
        stmt = stmt.where(RevenueEvent.occurred_at >= start)
    if end is not None:
        stmt = stmt.where(RevenueEvent.occurred_at < end)
    return stmt


async def _assert_content(
    db: AsyncSession, current: User, content_piece_id: str | None
) -> UUID | None:
    if not content_piece_id:
        return None
    try:
        cp_id = UUID(content_piece_id)
    except ValueError:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid content_piece_id")
    if not await authz_client.check(
        str(current.id), "reader", f"content_piece:{cp_id}"
    ):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not permitted for this content")
    row = await db.execute(
        select(ContentPiece.id).where(
            ContentPiece.id == cp_id,
            ContentPiece.tenant_id == current.tenant_id,
            ContentPiece.is_deleted.is_(False),
        )
    )
    if not row.scalar_one_or_none():
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Content piece not found")
    return cp_id


async def _summary_for_period(
    db: AsyncSession,
    current: User,
    *,
    content_piece_id: UUID | None = None,
    start: datetime | None = None,
    end: datetime | None = None,
) -> AttributionSummaryOut:
    stmt = select(
        RevenueEvent.event_type,
        func.coalesce(func.sum(RevenueEvent.event_count), 0),
        func.coalesce(func.sum(RevenueEvent.amount_cents), 0),
    ).where(
        RevenueEvent.tenant_id == current.tenant_id,
        RevenueEvent.is_deleted.is_(False),
    )
    if content_piece_id:
        stmt = stmt.where(RevenueEvent.content_piece_id == content_piece_id)
    stmt = _apply_period(stmt, start, end).group_by(RevenueEvent.event_type)
    row = await db.execute(stmt)
    counts = {event_type.value: 0 for event_type in RevenueEventType}
    revenue_cents = 0
    total = 0
    for event_type, count, amount in row.all():
        key = event_type.value
        counts[key] = int(count)
        total += int(count)
        if event_type == RevenueEventType.REVENUE:
            revenue_cents += int(amount or 0)
    return AttributionSummaryOut(
        events=total,
        visits=counts["VISIT"],
        signups=counts["SIGNUP"],
        leads=counts["LEAD"],
        customers=counts["CUSTOMER"],
        revenue_cents=revenue_cents,
    )


def _summary_from_counts(counts: dict[str, int]) -> AttributionSummaryOut:
    return AttributionSummaryOut(
        events=counts["events"],
        visits=counts["visits"],
        signups=counts["signups"],
        leads=counts["leads"],
        customers=counts["customers"],
        revenue_cents=counts["revenue_cents"],
    )


def _summary_deltas(
    current: AttributionSummaryOut, previous: AttributionSummaryOut
) -> dict[str, AttributionDeltaOut]:
    fields = (
        "events",
        "visits",
        "signups",
        "leads",
        "customers",
        "revenue_cents",
    )
    return {
        field: AttributionDeltaOut(
            **trend_delta(int(getattr(current, field)), int(getattr(previous, field)))
        )
        for field in fields
    }


async def _channel_counts_for_period(
    db: AsyncSession,
    current: User,
    *,
    start: datetime,
    end: datetime,
) -> dict[str, dict[str, int]]:
    stmt = _apply_period(
        select(RevenueEvent).where(
            RevenueEvent.tenant_id == current.tenant_id,
            RevenueEvent.channel.is_not(None),
            RevenueEvent.is_deleted.is_(False),
        ),
        start,
        end,
    )
    rows = await db.execute(stmt)
    by_channel: dict[str, dict[str, int]] = {}
    for event in rows.scalars().all():
        channel = event.channel or "unknown"
        counts = by_channel.setdefault(channel, _empty_counts())
        _apply_event(counts, event)
    return by_channel


async def _source_counts_for_period(
    db: AsyncSession,
    current: User,
    *,
    start: datetime,
    end: datetime,
) -> dict[str, dict[str, int]]:
    stmt = _apply_period(
        select(RevenueEvent).where(
            RevenueEvent.tenant_id == current.tenant_id,
            RevenueEvent.source_url.is_not(None),
            RevenueEvent.is_deleted.is_(False),
        ),
        start,
        end,
    )
    rows = await db.execute(stmt)
    by_source: dict[str, dict[str, int]] = {}
    for event in rows.scalars().all():
        source = event.source_url or "unknown"
        counts = by_source.setdefault(source, _empty_counts())
        _apply_event(counts, event)
    return by_source


async def _content_counts_for_period(
    db: AsyncSession,
    current: User,
    *,
    start: datetime,
    end: datetime,
) -> dict[UUID, dict[str, int]]:
    stmt = _apply_period(
        select(RevenueEvent).where(
            RevenueEvent.tenant_id == current.tenant_id,
            RevenueEvent.content_piece_id.is_not(None),
            RevenueEvent.is_deleted.is_(False),
        ),
        start,
        end,
    )
    rows = await db.execute(stmt)
    by_content: dict[UUID, dict[str, int]] = {}
    for event in rows.scalars().all():
        if not event.content_piece_id:
            continue
        counts = by_content.setdefault(event.content_piece_id, _empty_counts())
        _apply_event(counts, event)
    return by_content


async def _assert_tenant_writer(current: User) -> None:
    if not await authz_client.check(
        str(current.id), "writer", f"tenant:{current.tenant_id}"
    ):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not permitted for this tenant")


async def _assert_tenant_reader(current: User) -> None:
    if not await authz_client.check(
        str(current.id), "reader", f"tenant:{current.tenant_id}"
    ):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not permitted for this tenant")


async def _load_connector(
    db: AsyncSession,
    current: User,
    connector_id: UUID,
) -> AnalyticsConnector:
    row = await db.execute(
        select(AnalyticsConnector).where(
            AnalyticsConnector.id == connector_id,
            AnalyticsConnector.tenant_id == current.tenant_id,
            AnalyticsConnector.is_deleted.is_(False),
        )
    )
    connector = row.scalar_one_or_none()
    if not connector:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Connector not found")
    return connector


async def _load_public_tenant(db: AsyncSession, tenant_slug: str) -> Tenant:
    row = await db.execute(
        select(Tenant).where(Tenant.slug == tenant_slug, Tenant.is_active.is_(True))
    )
    tenant = row.scalar_one_or_none()
    if not tenant:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Tenant not found")
    return tenant


async def _public_owner_id(db: AsyncSession, tenant_id: UUID) -> UUID:
    row = await db.execute(
        select(User.id)
        .where(User.tenant_id == tenant_id, User.is_active.is_(True))
        .order_by(User.created_at.asc())
    )
    owner_id = row.scalar_one_or_none()
    if not owner_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Tenant user not found")
    return owner_id


async def _public_content_id(
    db: AsyncSession, tenant_id: UUID, content_piece_id: str | None
) -> UUID | None:
    if not content_piece_id:
        return None
    try:
        cp_id = UUID(content_piece_id)
    except ValueError:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid content_piece_id")
    row = await db.execute(
        select(ContentPiece.id).where(
            ContentPiece.id == cp_id,
            ContentPiece.tenant_id == tenant_id,
            ContentPiece.is_deleted.is_(False),
        )
    )
    if not row.scalar_one_or_none():
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Content piece not found")
    return cp_id


def _request_source_url(request: Request, source_url: str | None) -> str | None:
    return source_url or request.headers.get("referer")


def _tracking_metadata(request: Request, extra: dict | None = None) -> dict:
    metadata = {
        "provider": "tracking_pixel",
        "channel": "first_party",
        "user_agent": request.headers.get("user-agent"),
        "ip_hint": request.client.host if request.client else None,
    }
    metadata.update(extra or {})
    return {k: v for k, v in metadata.items() if v is not None}


async def _upsert_import_event(
    db: AsyncSession,
    *,
    base: dict,
    event_type: RevenueEventType,
    event_count: int,
    amount_cents: int,
    cache: dict[str, RevenueEvent],
) -> bool:
    key = event_dedupe_key(
        tenant_id=base["tenant_id"],
        provider=base["provider"],
        event_type=event_type.value,
        content_piece_id=base["content_piece_id"],
        source_url=base["source_url"],
        occurred_at=base["occurred_at"],
        external_id=base["external_id"],
    )
    event = cache.get(key)
    if event is None:
        existing = await db.execute(
            select(RevenueEvent).where(
                RevenueEvent.tenant_id == base["tenant_id"],
                RevenueEvent.dedupe_key == key,
                RevenueEvent.is_deleted.is_(False),
            )
        )
        event = existing.scalar_one_or_none()
    if event:
        event.owner_id = base["owner_id"]
        event.content_piece_id = base["content_piece_id"]
        event.event_count = event_count
        event.amount_cents = amount_cents
        event.currency = base["currency"]
        event.provider = base["provider"]
        event.channel = base["channel"]
        event.source_url = base["source_url"]
        event.occurred_at = base["occurred_at"]
        event.metadata_json = base["metadata_json"]
        cache[key] = event
        return False

    event = RevenueEvent(
        tenant_id=base["tenant_id"],
        owner_id=base["owner_id"],
        content_piece_id=base["content_piece_id"],
        event_type=event_type,
        event_count=event_count,
        amount_cents=amount_cents,
        currency=base["currency"],
        provider=base["provider"],
        channel=base["channel"],
        dedupe_key=key,
        source_url=base["source_url"],
        occurred_at=base["occurred_at"],
        metadata_json=base["metadata_json"],
    )
    db.add(event)
    cache[key] = event
    return True


@router.get("/pixel.gif", include_in_schema=False)
async def tracking_pixel(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    tenant: str = Query(min_length=1, max_length=64),
    content_piece_id: str | None = None,
    source_url: str | None = Query(default=None, max_length=600),
):
    tenant_row = await _load_public_tenant(db, tenant)
    owner_id = await _public_owner_id(db, tenant_row.id)
    cp_id = await _public_content_id(db, tenant_row.id, content_piece_id)
    event = RevenueEvent(
        tenant_id=tenant_row.id,
        owner_id=owner_id,
        content_piece_id=cp_id,
        event_type=RevenueEventType.VISIT,
        event_count=1,
        amount_cents=0,
        currency="USD",
        provider="tracking_pixel",
        channel="first_party",
        source_url=_request_source_url(request, source_url),
        occurred_at=datetime.now(timezone.utc),
        metadata_json=_tracking_metadata(request),
    )
    db.add(event)
    await db.commit()
    return Response(
        content=PIXEL_GIF,
        media_type="image/gif",
        headers={
            "Cache-Control": "no-store, max-age=0",
            "Pragma": "no-cache",
        },
    )


@router.post(
    "/track", response_model=PublicTrackOut, status_code=status.HTTP_201_CREATED
)
async def track_event(
    request: Request,
    payload: PublicTrackEvent,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    tenant = await _load_public_tenant(db, payload.tenant_slug)
    owner_id = await _public_owner_id(db, tenant.id)
    cp_id = await _public_content_id(db, tenant.id, payload.content_piece_id)
    try:
        event_type = RevenueEventType(payload.event_type)
    except ValueError:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, f"Unknown event_type: {payload.event_type}"
        )
    occurred_at = datetime.now(timezone.utc)
    source_url = _request_source_url(request, payload.source_url)
    dedupe_key = (
        event_dedupe_key(
            tenant_id=tenant.id,
            provider="tracking_pixel",
            event_type=event_type.value,
            content_piece_id=cp_id,
            source_url=source_url,
            occurred_at=occurred_at,
            external_id=payload.external_id,
        )
        if payload.external_id
        else None
    )
    if dedupe_key:
        existing = await db.execute(
            select(RevenueEvent).where(
                RevenueEvent.tenant_id == tenant.id,
                RevenueEvent.dedupe_key == dedupe_key,
                RevenueEvent.is_deleted.is_(False),
            )
        )
        existing_event = existing.scalar_one_or_none()
        if existing_event:
            return PublicTrackOut(ok=True, event_id=str(existing_event.id))
    event = RevenueEvent(
        tenant_id=tenant.id,
        owner_id=owner_id,
        content_piece_id=cp_id,
        event_type=event_type,
        event_count=1,
        amount_cents=payload.amount_cents
        if event_type == RevenueEventType.REVENUE
        else 0,
        currency=payload.currency,
        provider="tracking_pixel",
        channel="first_party",
        dedupe_key=dedupe_key,
        source_url=source_url,
        occurred_at=occurred_at,
        metadata_json=_tracking_metadata(
            request,
            {
                **({"external_id": payload.external_id} if payload.external_id else {}),
                **(payload.metadata or {}),
            },
        ),
    )
    db.add(event)
    await db.commit()
    await db.refresh(event)
    return PublicTrackOut(ok=True, event_id=str(event.id))


@router.post(
    "/events", response_model=RevenueEventOut, status_code=status.HTTP_201_CREATED
)
async def create_event(
    payload: RevenueEventCreate,
    current: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    await _assert_tenant_writer(current)
    try:
        event_type = RevenueEventType(payload.event_type)
    except ValueError:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, f"Unknown event_type: {payload.event_type}"
        )
    cp_id = await _assert_content(db, current, payload.content_piece_id)
    event = RevenueEvent(
        tenant_id=current.tenant_id,
        owner_id=current.id,
        content_piece_id=cp_id,
        event_type=event_type,
        event_count=payload.event_count,
        amount_cents=payload.amount_cents,
        currency=payload.currency,
        provider=payload.provider,
        channel=normalize_channel(
            payload.provider or "manual", payload.source_url, payload.channel
        ),
        dedupe_key=payload.dedupe_key,
        source_url=payload.source_url,
        occurred_at=payload.occurred_at or datetime.now(timezone.utc),
        metadata_json=payload.metadata,
    )
    db.add(event)
    await db.commit()
    await db.refresh(event)
    return _out(event)


@router.get("/events", response_model=list[RevenueEventOut])
async def list_events(
    current: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    response: Response,
    page: Annotated[Page, Depends(pagination)],
    content_piece_id: str | None = None,
    days: int | None = Query(default=None, ge=1, le=365),
):
    cp_id = await _assert_content(db, current, content_piece_id)
    since = analytics_since(days)
    stmt = select(RevenueEvent).where(
        RevenueEvent.tenant_id == current.tenant_id,
        RevenueEvent.is_deleted.is_(False),
    )
    if cp_id:
        stmt = stmt.where(RevenueEvent.content_piece_id == cp_id)
    stmt = _apply_since(stmt, since)
    base = stmt.order_by(RevenueEvent.occurred_at.desc())
    paged = await paginate(db, base, page, response)
    row = await db.execute(paged)
    return [_out(event) for event in row.scalars().all()]


@router.get("/tracking/status", response_model=TrackingStatusOut)
async def tracking_status(
    current: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    days: int | None = Query(default=None, ge=1, le=365),
):
    await _assert_tenant_reader(current)
    since = analytics_since(days)
    stmt = _apply_since(
        select(RevenueEvent).where(
            RevenueEvent.tenant_id == current.tenant_id,
            RevenueEvent.provider == "tracking_pixel",
            RevenueEvent.channel == "first_party",
            RevenueEvent.is_deleted.is_(False),
        ),
        since,
    )
    rows = await db.execute(stmt)
    total = 0
    visits = 0
    conversions = 0
    last_seen_at: datetime | None = None
    for event in rows.scalars().all():
        event_count = event.event_count or 1
        total += event_count
        if event.event_type == RevenueEventType.VISIT:
            visits += event_count
        else:
            conversions += event_count
        if last_seen_at is None or event.occurred_at > last_seen_at:
            last_seen_at = event.occurred_at
    return TrackingStatusOut(
        installed=total > 0,
        events=total,
        first_party_visits=visits,
        first_party_conversions=conversions,
        last_seen_at=last_seen_at,
    )


async def _import_rows(
    db: AsyncSession,
    current: User,
    provider: str,
    rows: list[AnalyticsImportRow],
) -> AnalyticsImportOut:
    await _assert_tenant_writer(current)
    imported = 0
    cache: dict[str, RevenueEvent] = {}
    for row in rows:
        cp_id = await _assert_content(db, current, row.content_piece_id)
        occurred_at = row.occurred_at or datetime.now(timezone.utc)
        channel = normalize_channel(provider, row.source_url, row.channel)
        base = {
            "tenant_id": current.tenant_id,
            "owner_id": current.id,
            "content_piece_id": cp_id,
            "currency": row.currency,
            "provider": provider,
            "channel": channel,
            "source_url": row.source_url,
            "occurred_at": occurred_at,
            "external_id": row.external_id,
            "metadata_json": {
                "provider": provider,
                "channel": channel,
                **({"external_id": row.external_id} if row.external_id else {}),
                **(row.metadata or {}),
            },
        }
        for event_type, count in (
            (RevenueEventType.VISIT, row.visits),
            (RevenueEventType.SIGNUP, row.signups),
            (RevenueEventType.LEAD, row.leads),
            (RevenueEventType.CUSTOMER, row.customers),
        ):
            if count:
                created = await _upsert_import_event(
                    db,
                    base=base,
                    event_type=event_type,
                    event_count=count,
                    amount_cents=0,
                    cache=cache,
                )
                if created:
                    imported += 1
        if row.revenue_cents:
            created = await _upsert_import_event(
                db,
                base=base,
                event_type=RevenueEventType.REVENUE,
                event_count=1,
                amount_cents=row.revenue_cents,
                cache=cache,
            )
            if created:
                imported += 1
    await db.commit()
    return AnalyticsImportOut(imported_events=imported, imported_rows=len(rows))


@router.post("/import", response_model=AnalyticsImportOut)
async def import_events(
    payload: AnalyticsImportRequest,
    current: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await _import_rows(db, current, payload.provider, payload.rows)


@router.post("/import/csv", response_model=AnalyticsImportOut)
async def import_events_csv(
    current: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    file: UploadFile,
    provider: Annotated[str, Query(pattern=r"^(ga4|gsc|manual)$")] = "manual",
):
    if file.content_type not in CSV_CONTENT_TYPES and not (
        file.filename or ""
    ).lower().endswith(".csv"):
        raise HTTPException(
            status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, "Expected a .csv file"
        )
    data = await file.read(MAX_IMPORT_CSV_BYTES + 1)
    if len(data) > MAX_IMPORT_CSV_BYTES:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "CSV too large")
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "CSV must be UTF-8 encoded"
        ) from exc

    reader = csv.DictReader(io.StringIO(text))
    if reader.fieldnames is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "CSV has no header row")
    unknown = set(reader.fieldnames) - CSV_IMPORT_COLUMNS
    if unknown:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Unknown CSV column(s): {', '.join(sorted(unknown))}",
        )

    rows: list[AnalyticsImportRow] = []
    for line_no, raw in enumerate(reader, start=2):
        try:
            rows.append(_csv_row_to_import_row(raw))
        except (ValueError, ValidationError) as exc:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST, f"Row {line_no}: {exc}"
            ) from exc
    if not rows:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "CSV has no data rows")
    if len(rows) > MAX_IMPORT_CSV_ROWS:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"CSV has {len(rows)} rows; max is {MAX_IMPORT_CSV_ROWS}",
        )

    return await _import_rows(db, current, provider, rows)


@router.get("/connectors", response_model=list[AnalyticsConnectorOut])
async def list_connectors(
    current: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    await _assert_tenant_reader(current)
    rows = await db.execute(
        select(AnalyticsConnector)
        .where(
            AnalyticsConnector.tenant_id == current.tenant_id,
            AnalyticsConnector.is_deleted.is_(False),
        )
        .order_by(AnalyticsConnector.updated_at.desc())
    )
    return [_connector_out(connector) for connector in rows.scalars().all()]


@router.post(
    "/connectors",
    response_model=AnalyticsConnectorOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_connector(
    payload: AnalyticsConnectorCreate,
    current: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    await _assert_tenant_writer(current)
    provider = AnalyticsConnectorProvider(payload.provider)
    connector = AnalyticsConnector(
        tenant_id=current.tenant_id,
        owner_id=current.id,
        provider=provider,
        status=AnalyticsConnectorStatus.NEEDS_AUTH,
        display_name=payload.display_name.strip(),
        external_property_id=payload.external_property_id,
        site_url=payload.site_url,
        scopes=google_scopes(provider.value),
        metadata_json=payload.metadata,
    )
    db.add(connector)
    await db.commit()
    await db.refresh(connector)
    return _connector_out(connector)


@router.post(
    "/connectors/{connector_id}/disconnect", response_model=AnalyticsConnectorOut
)
async def disconnect_connector(
    connector_id: UUID,
    current: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    await _assert_tenant_writer(current)
    connector = await _load_connector(db, current, connector_id)
    connector.status = AnalyticsConnectorStatus.DISCONNECTED
    metadata = dict(connector.metadata_json or {})
    metadata.pop("oauth", None)
    connector.metadata_json = metadata or None
    await db.commit()
    await db.refresh(connector)
    return _connector_out(connector)


@router.post(
    "/connectors/{connector_id}/google/callback",
    response_model=AnalyticsConnectorOut,
)
async def google_connector_callback(
    connector_id: UUID,
    payload: AnalyticsConnectorCallback,
    current: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    await _assert_tenant_writer(current)
    if not (
        settings.GOOGLE_OAUTH_CLIENT_ID
        and settings.GOOGLE_OAUTH_CLIENT_SECRET
        and settings.GOOGLE_OAUTH_REDIRECT_URI
    ):
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Google OAuth is not configured.",
        )
    connector = await _load_connector(db, current, connector_id)
    if connector.provider not in (
        AnalyticsConnectorProvider.GA4,
        AnalyticsConnectorProvider.GSC,
    ):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "Connector is not Google-backed"
        )
    oauth_state = await consume_oauth_state(payload.state)
    if oauth_state is None:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "Invalid or expired OAuth state"
        )
    if oauth_state["tenant_id"] != str(current.tenant_id):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, "OAuth state belongs to another tenant"
        )
    if oauth_state["provider"] != connector.provider.value:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"OAuth state was issued for {oauth_state['provider']}, "
            f"not {connector.provider.value}",
        )
    try:
        token = await exchange_google_oauth_code(
            client_id=settings.GOOGLE_OAUTH_CLIENT_ID,
            client_secret=settings.GOOGLE_OAUTH_CLIENT_SECRET,
            redirect_uri=settings.GOOGLE_OAUTH_REDIRECT_URI,
            code=payload.code,
        )
    except GoogleOAuthError as e:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(e))
    metadata = dict(connector.metadata_json or {})
    metadata["oauth"] = {
        "access_token": token["access_token"],
        "refresh_token": token.get("refresh_token"),
        "expires_in": token.get("expires_in"),
        "token_type": token.get("token_type"),
        "scope": token.get("scope"),
    }
    connector.metadata_json = metadata
    connector.status = AnalyticsConnectorStatus.CONNECTED
    connector.last_sync_error = None
    await db.commit()
    await db.refresh(connector)
    return _connector_out(connector)


@router.post(
    "/connectors/{connector_id}/sync",
    response_model=AnalyticsConnectorSyncOut,
    status_code=status.HTTP_202_ACCEPTED,
)
async def sync_connector(
    connector_id: UUID,
    current: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    await _assert_tenant_writer(current)
    connector = await _load_connector(db, current, connector_id)
    if connector.status != AnalyticsConnectorStatus.CONNECTED:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Connector must be connected before sync.",
        )
    task = sync_analytics_connector.delay(str(connector.id))
    return AnalyticsConnectorSyncOut(
        connector_id=str(connector.id),
        task_id=task.id,
        status="QUEUED",
    )


@router.get("/connectors/google/auth-url", response_model=AnalyticsConnectorAuthUrlOut)
async def google_connector_auth_url(
    current: Annotated[User, Depends(get_current_user)],
    provider: str = Query(pattern=r"^(ga4|gsc)$"),
):
    await _assert_tenant_writer(current)
    scopes = google_scopes(provider)
    configured = bool(
        settings.GOOGLE_OAUTH_CLIENT_ID and settings.GOOGLE_OAUTH_REDIRECT_URI
    )
    if not configured:
        return AnalyticsConnectorAuthUrlOut(
            configured=False,
            provider=provider,
            scopes=scopes,
            message=(
                "Google OAuth is not configured. Set GOOGLE_OAUTH_CLIENT_ID "
                "and GOOGLE_OAUTH_REDIRECT_URI."
            ),
        )
    state = await issue_oauth_state(
        provider=provider, tenant_id=str(current.tenant_id), user_id=str(current.id)
    )
    return AnalyticsConnectorAuthUrlOut(
        configured=True,
        provider=provider,
        scopes=scopes,
        state=state,
        auth_url=build_google_auth_url(
            client_id=settings.GOOGLE_OAUTH_CLIENT_ID,
            redirect_uri=settings.GOOGLE_OAUTH_REDIRECT_URI,
            provider=provider,
            state=state,
        ),
    )


@router.get("/summary", response_model=AttributionSummaryOut)
async def attribution_summary(
    current: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    content_piece_id: str | None = None,
    days: int | None = Query(default=None, ge=1, le=365),
):
    cp_id = await _assert_content(db, current, content_piece_id)
    since = analytics_since(days)
    return await _summary_for_period(
        db,
        current,
        content_piece_id=cp_id,
        start=since,
        end=None,
    )


@router.get("/trends", response_model=AttributionTrendOut)
async def attribution_trends(
    current: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    content_piece_id: str | None = None,
    days: int = Query(default=30, ge=1, le=365),
):
    cp_id = await _assert_content(db, current, content_piece_id)
    previous_start, current_start, end = analytics_periods(days)
    current_summary = await _summary_for_period(
        db,
        current,
        content_piece_id=cp_id,
        start=current_start,
        end=end,
    )
    previous_summary = await _summary_for_period(
        db,
        current,
        content_piece_id=cp_id,
        start=previous_start,
        end=current_start,
    )
    return AttributionTrendOut(
        days=days,
        current=current_summary,
        previous=previous_summary,
        deltas=_summary_deltas(current_summary, previous_summary),
    )


@router.get("/channel-trends", response_model=list[ChannelTrendOut])
async def channel_trends(
    current: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    days: int = Query(default=30, ge=1, le=365),
):
    await _assert_tenant_reader(current)
    previous_start, current_start, end = analytics_periods(days)
    current_counts = await _channel_counts_for_period(
        db,
        current,
        start=current_start,
        end=end,
    )
    previous_counts = await _channel_counts_for_period(
        db,
        current,
        start=previous_start,
        end=current_start,
    )
    channels = set(current_counts) | set(previous_counts)
    results = []
    for channel in channels:
        current_summary = _summary_from_counts(
            current_counts.get(channel, _empty_counts())
        )
        previous_summary = _summary_from_counts(
            previous_counts.get(channel, _empty_counts())
        )
        results.append(
            ChannelTrendOut(
                channel=channel,
                current=current_summary,
                previous=previous_summary,
                deltas=_summary_deltas(current_summary, previous_summary),
            )
        )
    return sorted(
        results,
        key=lambda item: (
            item.current.revenue_cents,
            item.current.customers,
            item.current.leads,
            item.current.events,
        ),
        reverse=True,
    )


@router.get("/source-trends", response_model=list[SourceTrendOut])
async def source_trends(
    current: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    days: int = Query(default=30, ge=1, le=365),
):
    await _assert_tenant_reader(current)
    previous_start, current_start, end = analytics_periods(days)
    current_counts = await _source_counts_for_period(
        db,
        current,
        start=current_start,
        end=end,
    )
    previous_counts = await _source_counts_for_period(
        db,
        current,
        start=previous_start,
        end=current_start,
    )
    sources = set(current_counts) | set(previous_counts)
    results = []
    for source in sources:
        current_summary = _summary_from_counts(
            current_counts.get(source, _empty_counts())
        )
        previous_summary = _summary_from_counts(
            previous_counts.get(source, _empty_counts())
        )
        results.append(
            SourceTrendOut(
                source_url=source,
                current=current_summary,
                previous=previous_summary,
                deltas=_summary_deltas(current_summary, previous_summary),
            )
        )
    return sorted(
        results,
        key=lambda item: (
            item.current.revenue_cents,
            item.current.customers,
            item.current.leads,
            item.current.events,
        ),
        reverse=True,
    )


@router.get("/content-trends", response_model=list[ContentTrendOut])
async def content_trends(
    current: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    days: int = Query(default=30, ge=1, le=365),
):
    await _assert_tenant_reader(current)
    previous_start, current_start, end = analytics_periods(days)
    current_counts = await _content_counts_for_period(
        db,
        current,
        start=current_start,
        end=end,
    )
    previous_counts = await _content_counts_for_period(
        db,
        current,
        start=previous_start,
        end=current_start,
    )
    content_ids = set(current_counts) | set(previous_counts)
    if not content_ids:
        return []
    rows = await db.execute(
        select(ContentPiece).where(
            ContentPiece.id.in_(content_ids),
            ContentPiece.tenant_id == current.tenant_id,
            ContentPiece.is_deleted.is_(False),
        )
    )
    content_by_id = {item.id: item for item in rows.scalars().all()}
    results = []
    for content_id in content_ids:
        item = content_by_id.get(content_id)
        if not item:
            continue
        current_summary = _summary_from_counts(
            current_counts.get(content_id, _empty_counts())
        )
        previous_summary = _summary_from_counts(
            previous_counts.get(content_id, _empty_counts())
        )
        results.append(
            ContentTrendOut(
                content_piece_id=str(item.id),
                title=item.title,
                status=item.status.value,
                current=current_summary,
                previous=previous_summary,
                deltas=_summary_deltas(current_summary, previous_summary),
            )
        )
    return sorted(
        results,
        key=lambda item: (
            item.current.revenue_cents,
            item.current.customers,
            item.current.leads,
            item.current.events,
        ),
        reverse=True,
    )


@router.get("/content", response_model=list[ContentAttributionOut])
async def content_attribution(
    current: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    days: int | None = Query(default=None, ge=1, le=365),
):
    since = analytics_since(days)
    content_rows = await db.execute(
        select(ContentPiece).where(
            ContentPiece.tenant_id == current.tenant_id,
            ContentPiece.is_deleted.is_(False),
        )
    )
    content = list(content_rows.scalars().all())
    by_id = {item.id: _empty_counts() for item in content}
    event_stmt = _apply_since(
        select(RevenueEvent).where(
            RevenueEvent.tenant_id == current.tenant_id,
            RevenueEvent.content_piece_id.is_not(None),
            RevenueEvent.is_deleted.is_(False),
        ),
        since,
    )
    event_rows = await db.execute(event_stmt)
    for event in event_rows.scalars().all():
        if event.content_piece_id in by_id:
            _apply_event(by_id[event.content_piece_id], event)
    results = [
        ContentAttributionOut(
            content_piece_id=str(item.id),
            title=item.title,
            status=item.status.value,
            **by_id[item.id],
        )
        for item in content
    ]
    return sorted(
        results,
        key=lambda item: (item.revenue_cents, item.customers, item.leads, item.events),
        reverse=True,
    )


@router.get("/channels", response_model=list[ChannelAttributionOut])
async def channel_attribution(
    current: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    days: int | None = Query(default=None, ge=1, le=365),
):
    since = analytics_since(days)
    stmt = _apply_since(
        select(RevenueEvent).where(
            RevenueEvent.tenant_id == current.tenant_id,
            RevenueEvent.channel.is_not(None),
            RevenueEvent.is_deleted.is_(False),
        ),
        since,
    )
    rows = await db.execute(stmt)
    by_channel: dict[str, dict[str, int]] = {}
    for event in rows.scalars().all():
        channel = event.channel or "unknown"
        counts = by_channel.setdefault(channel, _empty_counts())
        _apply_event(counts, event)
    results = [
        ChannelAttributionOut(channel=channel, **counts)
        for channel, counts in by_channel.items()
    ]
    return sorted(
        results,
        key=lambda item: (item.revenue_cents, item.customers, item.leads, item.events),
        reverse=True,
    )


@router.get("/sources", response_model=list[SourceAttributionOut])
async def source_attribution(
    current: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    days: int | None = Query(default=None, ge=1, le=365),
):
    since = analytics_since(days)
    stmt = _apply_since(
        select(RevenueEvent).where(
            RevenueEvent.tenant_id == current.tenant_id,
            RevenueEvent.source_url.is_not(None),
            RevenueEvent.is_deleted.is_(False),
        ),
        since,
    )
    rows = await db.execute(stmt)
    by_source: dict[str, dict[str, int]] = {}
    for event in rows.scalars().all():
        source = event.source_url or "unknown"
        counts = by_source.setdefault(source, _empty_counts())
        _apply_event(counts, event)
    results = [
        SourceAttributionOut(source_url=source, **counts)
        for source, counts in by_source.items()
    ]
    return sorted(
        results,
        key=lambda item: (item.revenue_cents, item.customers, item.leads, item.events),
        reverse=True,
    )


# -----------------------------------------------------------------------------
# Attribution loop: "what to write/refresh next" recommendations, computed
# from real trend data by app.workers.tasks.generate_content_recommendations
# (daily beat sweep). This router only reads/actions the persisted rows —
# see that task for how scores are computed.
# -----------------------------------------------------------------------------
def _recommendation_out(rec: ContentRecommendation) -> ContentRecommendationOut:
    return ContentRecommendationOut(
        id=str(rec.id),
        kind=rec.kind.value,
        content_piece_id=str(rec.content_piece_id) if rec.content_piece_id else None,
        title=rec.title,
        rationale=rec.rationale,
        score=rec.score,
        status=rec.status.value,
        orchestrator_run_id=(
            str(rec.orchestrator_run_id) if rec.orchestrator_run_id else None
        ),
        created_at=rec.created_at,
    )


async def _load_recommendation(
    db: AsyncSession, tenant_id: UUID, rec_id: UUID
) -> ContentRecommendation:
    row = await db.execute(
        select(ContentRecommendation).where(
            ContentRecommendation.id == rec_id,
            ContentRecommendation.tenant_id == tenant_id,
            ContentRecommendation.is_deleted.is_(False),
        )
    )
    rec = row.scalar_one_or_none()
    if not rec:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Recommendation not found")
    return rec


@router.get("/recommendations", response_model=list[ContentRecommendationOut])
async def list_recommendations(
    current: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    status_filter: str | None = Query(default="PENDING", alias="status"),
):
    await _assert_tenant_reader(current)
    stmt = select(ContentRecommendation).where(
        ContentRecommendation.tenant_id == current.tenant_id,
        ContentRecommendation.is_deleted.is_(False),
    )
    if status_filter:
        try:
            stmt = stmt.where(
                ContentRecommendation.status
                == ContentRecommendationStatus(status_filter.upper())
            )
        except ValueError:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST, f"Unknown status: {status_filter}"
            )
    stmt = stmt.order_by(ContentRecommendation.score.desc())
    rows = await db.execute(stmt)
    return [_recommendation_out(r) for r in rows.scalars().all()]


@router.post(
    "/recommendations/{recommendation_id}/dismiss",
    response_model=ContentRecommendationOut,
)
async def dismiss_recommendation(
    recommendation_id: UUID,
    current: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    await _assert_tenant_writer(current)
    rec = await _load_recommendation(db, current.tenant_id, recommendation_id)
    if rec.status != ContentRecommendationStatus.PENDING:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"Recommendation already {rec.status.value.lower()}",
        )
    rec.status = ContentRecommendationStatus.DISMISSED
    await db.commit()
    await db.refresh(rec)
    return _recommendation_out(rec)


@router.post(
    "/recommendations/{recommendation_id}/start-run",
    response_model=ContentRecommendationOut,
)
async def start_run_from_recommendation(
    recommendation_id: UUID,
    current: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Turn a recommendation into a real orchestrator run — the attribution
    loop's actual feedback step. Reuses the real POST /orchestrator/runs
    handler rather than re-deriving run-creation logic (same "don't hand-
    copy business logic" precedent as the MCP tools' create_generation/
    create_orchestrator_run wiring)."""
    from app.routers.orchestrator import create_run
    from app.schemas.article import ArticleBrief
    from app.schemas.orchestrator import OrchestratorRunCreate

    await _assert_tenant_writer(current)
    rec = await _load_recommendation(db, current.tenant_id, recommendation_id)
    if rec.status != ContentRecommendationStatus.PENDING:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"Recommendation already {rec.status.value.lower()}",
        )

    article_kwargs: dict = {"notes": rec.rationale}
    if rec.content_piece_id:
        source = await db.get(ContentPiece, rec.content_piece_id)
        if source:
            src_article = (source.metadata_json or {}).get("article") or {}
            article_kwargs["topic"] = (
                f"Refresh: {source.title}"
                if rec.kind.value == "REFRESH"
                else f"Follow-up to: {source.title}"
            )
            for key in ("primary_keyword", "secondary_keywords", "tags", "audience"):
                if src_article.get(key):
                    article_kwargs[key] = src_article[key]
    if "topic" not in article_kwargs:
        article_kwargs["topic"] = rec.title

    run_out = await create_run(
        OrchestratorRunCreate(
            brief=article_kwargs["topic"],
            article=ArticleBrief(**article_kwargs),
        ),
        current,
        db,
    )

    rec.status = ContentRecommendationStatus.ACTIONED
    rec.orchestrator_run_id = UUID(run_out.run_id)
    await db.commit()
    await db.refresh(rec)
    return _recommendation_out(rec)


# -----------------------------------------------------------------------------
# Tenant-owned Stripe revenue sync: a tenant's OWN Stripe account (their
# downstream customers paying THEM). OpenGrow's core has no platform billing
# (removed in 0.3.0 — it lives in the private hosted overlay); this is BYOK
# per-tenant revenue attribution, mirroring app.routers.content's GitHub
# credential connect/disconnect pattern. Webhook signature verification is
# standard Stripe webhook handling, but scoped per tenant since each tenant
# has their own webhook secret stored on their credential row.
# -----------------------------------------------------------------------------
async def _load_tenant_stripe_credential(
    db: AsyncSession, tenant_id: UUID
) -> TenantStripeCredential | None:
    return await db.scalar(
        select(TenantStripeCredential).where(
            TenantStripeCredential.tenant_id == tenant_id,
            TenantStripeCredential.is_deleted.is_(False),
        )
    )


@router.get("/stripe/config", response_model=TenantStripeConfigOut)
async def tenant_stripe_config(
    request: Request,
    current: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    await _assert_tenant_reader(current)
    credential = await _load_tenant_stripe_credential(db, current.tenant_id)
    if credential is None:
        return TenantStripeConfigOut(configured=False)
    webhook_url = str(
        request.url_for("tenant_stripe_webhook", tenant_id=str(current.tenant_id))
    )
    return TenantStripeConfigOut(
        configured=True,
        secret_key_last4=credential.secret_key_last4,
        display_name=credential.display_name,
        webhook_url=webhook_url,
    )


@router.post(
    "/stripe/credentials",
    response_model=TenantStripeConfigOut,
    status_code=status.HTTP_201_CREATED,
)
async def upsert_tenant_stripe_credential(
    payload: TenantStripeCredentialUpsert,
    request: Request,
    current: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    await _assert_tenant_writer(current)
    try:
        stripe.StripeClient(payload.secret_key).v1.balance.retrieve()
    except stripe.AuthenticationError as e:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, f"Stripe rejected the secret key: {e}"
        ) from e
    except stripe.StripeError as e:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, f"Could not reach Stripe: {e}"
        ) from e

    try:
        secret_key_encrypted = encrypt_secret(payload.secret_key)
        webhook_secret_encrypted = encrypt_secret(payload.webhook_secret)
    except CredentialCryptoError as e:
        raise HTTPException(status.HTTP_409_CONFLICT, str(e)) from e

    credential = await _load_tenant_stripe_credential(db, current.tenant_id)
    if credential is None:
        credential = TenantStripeCredential(
            tenant_id=current.tenant_id,
            owner_id=current.id,
            secret_key_encrypted=secret_key_encrypted,
            secret_key_last4=payload.secret_key[-4:],
            webhook_secret_encrypted=webhook_secret_encrypted,
            display_name=payload.display_name,
        )
        db.add(credential)
    else:
        credential.owner_id = current.id
        credential.secret_key_encrypted = secret_key_encrypted
        credential.secret_key_last4 = payload.secret_key[-4:]
        credential.webhook_secret_encrypted = webhook_secret_encrypted
        credential.display_name = payload.display_name
    await record_audit_event(
        db,
        action="stripe_revenue.credentials.connected",
        tenant_id=current.tenant_id,
        actor_user_id=current.id,
        actor_email=current.email,
        details={"display_name": credential.display_name},
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    await db.commit()
    await db.refresh(credential)
    webhook_url = str(
        request.url_for("tenant_stripe_webhook", tenant_id=str(current.tenant_id))
    )
    return TenantStripeConfigOut(
        configured=True,
        secret_key_last4=credential.secret_key_last4,
        display_name=credential.display_name,
        webhook_url=webhook_url,
    )


@router.delete("/stripe/credentials", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tenant_stripe_credential(
    request: Request,
    current: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    await _assert_tenant_writer(current)
    credential = await _load_tenant_stripe_credential(db, current.tenant_id)
    if credential is None:
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    credential.is_deleted = True
    await record_audit_event(
        db,
        action="stripe_revenue.credentials.disconnected",
        tenant_id=current.tenant_id,
        actor_user_id=current.id,
        actor_email=current.email,
        details={},
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def _stripe_charge_to_revenue_event(
    tenant_id: UUID, owner_id: UUID, charge: dict
) -> RevenueEvent:
    meta = charge.get("metadata") or {}
    content_piece_id = None
    if meta.get("content_piece_id"):
        try:
            content_piece_id = UUID(meta["content_piece_id"])
        except ValueError:
            content_piece_id = None
    source_url = meta.get("source_url")
    occurred_at = datetime.fromtimestamp(charge["created"], tz=timezone.utc)
    channel = normalize_channel("stripe", source_url, meta.get("channel"))
    dedupe_key = event_dedupe_key(
        tenant_id=tenant_id,
        provider="stripe",
        event_type=RevenueEventType.REVENUE.value,
        content_piece_id=content_piece_id,
        source_url=source_url,
        occurred_at=occurred_at,
        external_id=charge["id"],
    )
    return RevenueEvent(
        tenant_id=tenant_id,
        owner_id=owner_id,
        content_piece_id=content_piece_id,
        event_type=RevenueEventType.REVENUE,
        event_count=1,
        amount_cents=charge["amount_received"],
        currency=(charge.get("currency") or "usd").upper(),
        provider="stripe",
        channel=channel,
        dedupe_key=dedupe_key,
        source_url=source_url,
        occurred_at=occurred_at,
        metadata_json={"stripe_charge_id": charge["id"]},
    )


@router.post("/stripe/webhook/{tenant_id}", status_code=status.HTTP_200_OK)
async def tenant_stripe_webhook(
    tenant_id: UUID,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Unauthenticated by design (Stripe can't send a bearer token) — trust
    comes entirely from the signature check against THIS tenant's stored
    webhook_secret. The tenant_id in the path only selects which secret to
    verify against; it grants nothing on its own."""
    credential = await _load_tenant_stripe_credential(db, tenant_id)
    if credential is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Stripe not connected")
    try:
        webhook_secret = decrypt_secret(credential.webhook_secret_encrypted)
    except CredentialCryptoError:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "Stored webhook secret is unusable"
        )

    body = await request.body()
    sig_header = request.headers.get("stripe-signature", "")
    try:
        event = stripe.Webhook.construct_event(body, sig_header, webhook_secret)
    except (ValueError, stripe.SignatureVerificationError) as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Invalid webhook: {e}") from e

    existing = await db.scalar(
        select(TenantStripeWebhookEvent).where(
            TenantStripeWebhookEvent.tenant_id == tenant_id,
            TenantStripeWebhookEvent.stripe_event_id == event["id"],
        )
    )
    if existing:
        return {"status": "already_processed"}

    event_type = event["type"]
    if event_type == "charge.succeeded":
        charge = event["data"]["object"]
        if charge.get("paid") and charge.get("amount_received", 0) > 0:
            db.add(
                _stripe_charge_to_revenue_event(tenant_id, credential.owner_id, charge)
            )

    db.add(
        TenantStripeWebhookEvent(
            id=uuid4(),
            tenant_id=tenant_id,
            stripe_event_id=event["id"],
            event_type=event_type,
            payload=event.to_dict_recursive(),
            processed_at=datetime.now(timezone.utc),
        )
    )
    await db.commit()
    return {"status": "processed"}
