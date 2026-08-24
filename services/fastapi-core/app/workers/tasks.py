"""Celery tasks. All long-running work (scan / embed / generate) runs here."""

from __future__ import annotations
import asyncio
import json
import logging
import re
import smtplib
from datetime import datetime, timezone
from email.message import EmailMessage
from uuid import UUID, uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.celery_app import celery
from app.config import settings
from app.core.analytics_import import event_dedupe_key, normalize_channel
from app.core.brand_scraper import UnsafeURLError, fetch_site
from app.core.clamav import scan_bytes
from app.core.google_analytics import (
    default_sync_window,
    fetch_ga4_rows,
    fetch_gsc_rows,
)
from app.core.google_oauth import refresh_google_access_token
from app.core.litellm_client import chat_completion, embed
from app.core.minio_client import get_object_bytes, promote_to_assets
from app.core.qdrant import upsert_asset_embedding
from app.core.analytics_window import analytics_periods
from app.core.article_grounding import ground_article
from app.core.content_recommendations import build_recommendations
from app.core.credential_crypto import CredentialCryptoError, decrypt_secret
from app.core.credits import grant_credits_sync, real_generation_cost_cents
from app.core.generation_messages import build_generation_messages
from app.core.github_publisher import GitHubPublishError
from app.core.publishers import PublisherError, get_adapter
from app.core.usage import record_usage_sync
from app.models.analytics import RevenueEvent, RevenueEventType
from app.models.asset import Asset, AssetStatus
from app.models.analytics_connector import (
    AnalyticsConnector,
    AnalyticsConnectorProvider,
    AnalyticsConnectorStatus,
)
from app.models.brand import Brand, BrandStatus
from app.models.content_piece import ContentPiece, ContentStatus
from app.models.content_recommendation import (
    ContentRecommendation,
    ContentRecommendationKind,
    ContentRecommendationStatus,
)
from app.models.generation import Generation, GenerationStatus
from app.models.github_credential import GitHubCredential
from app.models.publication import Publication, PublicationChannel, PublicationStatus
from app.models.tenant import Tenant

log = logging.getLogger("worker")

# Celery uses a sync engine (worker context, not asyncio-friendly at top level)
_sync_engine = create_engine(
    settings.postgres_sync_dsn, pool_pre_ping=True, pool_size=5
)
_SyncSession = sessionmaker(_sync_engine, expire_on_commit=False)


def asset_snippet(text: str | None, limit: int = 2000) -> str:
    return (text or "").strip()[:limit]


def _run(coro):
    """Bridge asyncio → celery sync task."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            raise RuntimeError("already running")
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)


# -----------------------------------------------------------------------------
# ClamAV scan (cpu_light queue)
# -----------------------------------------------------------------------------
@celery.task(
    bind=True,
    name="app.workers.tasks.scan_asset",
    max_retries=3,
    default_retry_delay=10,
)
def scan_asset(self, asset_id: str) -> str:
    with _SyncSession() as db:
        asset = db.get(Asset, UUID(asset_id))
        if not asset:
            log.warning("scan_asset: asset %s missing", asset_id)
            return "missing"

        asset.status = AssetStatus.SCANNING
        db.commit()

        try:
            blob = get_object_bytes(settings.MINIO_BUCKET_TEMP, asset.temp_object_key)
        except Exception as e:
            asset.status = AssetStatus.SCAN_FAILED
            asset.scan_message = f"fetch failed: {e.__class__.__name__}"
            db.commit()
            return "fetch_failed"

        clean, msg = scan_bytes(blob)
        if not clean:
            asset.status = AssetStatus.SCAN_FAILED
            asset.scan_message = msg
            db.commit()
            return "infected"

        target_key = asset.temp_object_key.replace("/", "/", 1)  # keep hierarchy
        try:
            promote_to_assets(asset.temp_object_key, target_key)
        except Exception as e:
            asset.status = AssetStatus.SCAN_FAILED
            asset.scan_message = f"promote failed: {e.__class__.__name__}"
            db.commit()
            return "promote_failed"

        asset.object_key = target_key
        asset.status = AssetStatus.SCANNED
        asset.scan_message = "clean"
        db.commit()

    embed_asset.delay(asset_id)
    return "ok"


# -----------------------------------------------------------------------------
# LiteLLM embedding + Qdrant upsert (cpu_light queue)
# -----------------------------------------------------------------------------
@celery.task(
    bind=True,
    name="app.workers.tasks.embed_asset",
    max_retries=3,
    default_retry_delay=15,
)
def embed_asset(self, asset_id: str) -> str:
    with _SyncSession() as db:
        asset = db.get(Asset, UUID(asset_id))
        if not asset or asset.status != AssetStatus.SCANNED:
            return "skip"
        asset.status = AssetStatus.EMBEDDING
        db.commit()

        try:
            # Text assets: use raw bytes. Binary: use filename + content-type as proxy.
            if asset.content_type.startswith("text/"):
                blob = get_object_bytes(settings.MINIO_BUCKET_ASSETS, asset.object_key)
                text = blob.decode("utf-8", errors="ignore")[:20_000]
            else:
                text = (
                    f"{asset.filename} [{asset.content_type}] tenant={asset.tenant_id}"
                )

            vec = _run(embed(text))
            asset.embedding = vec
            asset.text_snippet = asset_snippet(text)
            if not settings.is_lite:
                _run(
                    upsert_asset_embedding(
                        asset_id=str(asset.id),
                        tenant_id=str(asset.tenant_id),
                        vector=vec,
                        meta={
                            "filename": asset.filename,
                            "content_type": asset.content_type,
                            "text_snippet": asset_snippet(text, 1000),
                        },
                    )
                )
            # Embedding + snippet are persisted on the Asset row in both modes; lite
            # ranks them in Postgres, production also mirrors the vector into Qdrant.
            asset.status = AssetStatus.INDEXED
            db.commit()
            return "ok"
        except Exception as e:
            asset.status = AssetStatus.EMBED_FAILED
            asset.scan_message = f"embed failed: {e.__class__.__name__}"
            db.commit()
            raise self.retry(exc=e)


# -----------------------------------------------------------------------------
# LLM generation (gen_heavy queue)
# -----------------------------------------------------------------------------
@celery.task(
    bind=True,
    name="app.workers.tasks.run_generation",
    max_retries=2,
    default_retry_delay=30,
)
def run_generation(self, generation_id: str) -> str:
    with _SyncSession() as db:
        gen = db.get(Generation, UUID(generation_id))
        if not gen:
            return "missing"
        gen.status = GenerationStatus.RUNNING
        db.commit()

        # Article generations get brand + retrieved-asset grounding via the
        # shared helper (additive: failures inside never fail the run). The
        # results feed the prompt builder directly — they are NOT written
        # back into metadata_json (internal inputs don't belong in the row).
        brand = None
        context: list[dict] = []
        meta = gen.metadata_json or {}
        if meta.get("kind") in ("article_outline", "article_draft"):
            brand, context = ground_article(
                db, gen.tenant_id, meta.get("article") or {}
            )

        messages, max_tokens = build_generation_messages(
            db, gen, brand=brand, context=context
        )
        model = (gen.metadata_json or {}).get("model") or settings.DEFAULT_LLM_MODEL
        hold_cents = meta.get("credit_hold_cents")
        try:
            content, raw_response = _run(
                chat_completion(messages=messages, model=model, max_tokens=max_tokens)
            )
            gen.result = content
            gen.status = GenerationStatus.COMPLETE
            db.commit()
        except Exception as e:
            gen.status = GenerationStatus.FAILED
            gen.error_message = f"{e.__class__.__name__}: {e}"[:500]
            db.commit()
            # Refund the full hold — no charge for a failed generation. This
            # task retries (max_retries=2): only refund once self.retry()
            # itself gives up (raises the original exception rather than a
            # Retry that Celery will re-drive), otherwise each retry attempt
            # would refund the same hold again while the row is still queued
            # to try the LLM call once more.
            is_final_attempt = self.request.retries >= self.max_retries
            if hold_cents and is_final_attempt:
                grant_credits_sync(
                    db, tenant_id=gen.tenant_id, amount_cents=hold_cents
                )
            raise self.retry(exc=e)

        # Settle the hold to the real cost. Only ever refunds the
        # difference (real cost is bounded by the same max_tokens the hold
        # was computed from) — never charges more than what was held.
        if hold_cents:
            try:
                real_cents = real_generation_cost_cents(raw_response)
            except Exception:
                real_cents = hold_cents  # pricing lookup failed — no refund, not a loss
            refund_cents = max(0, hold_cents - real_cents)
            if refund_cents:
                grant_credits_sync(
                    db, tenant_id=gen.tenant_id, amount_cents=refund_cents
                )

    notify_email.delay(generation_id, "complete")
    return "ok"


@celery.task(
    bind=True,
    name="app.workers.tasks.run_orchestrator",
    max_retries=1,
    default_retry_delay=30,
)
def run_orchestrator(self, run_id: str) -> str:
    """Drive an orchestrator run (generate → promote). Logic lives in
    app.core.orchestrator.execute_run so it's unit-testable."""
    from app.core.orchestrator import execute_run

    with _SyncSession() as db:
        try:
            return execute_run(db, run_id)
        except Exception as e:  # execute_run already marked the run FAILED
            raise self.retry(exc=e)


# -----------------------------------------------------------------------------
# Notification email (Mailpit local, SMTP prod)
# -----------------------------------------------------------------------------
@celery.task(name="app.workers.tasks.notify_email")
def notify_email(generation_id: str, event: str) -> str:
    with _SyncSession() as db:
        gen = db.get(Generation, UUID(generation_id))
        if not gen:
            return "missing"

        msg = EmailMessage()
        msg["From"] = "opengrow@opengrow.local"
        msg["To"] = f"tenant-{gen.tenant_id}@opengrow.local"
        msg["Subject"] = f"OpenGrow: generation {gen.id} {event}"
        msg.set_content(
            f"Generation {gen.id} finished with status={gen.status.value}\n\n"
            f"Brief: {gen.brief[:200]}"
        )
        try:
            with smtplib.SMTP(
                settings.MAILPIT_HOST, settings.MAILPIT_SMTP_PORT, timeout=10
            ) as s:
                s.send_message(msg)
        except Exception as e:
            log.warning("notify_email failed: %s", e)
            return "smtp_failed"
    return "ok"


@celery.task(name="app.workers.tasks.refresh_clamav_signatures")
def refresh_clamav_signatures() -> str:
    # ClamAV auto-refreshes via freshclam; hook is a placeholder for future logic.
    return "noop"


def _connector_row_events(row: dict) -> tuple[tuple[RevenueEventType, int, int], ...]:
    return (
        (RevenueEventType.VISIT, int(row.get("visits") or 0), 0),
        (RevenueEventType.SIGNUP, int(row.get("signups") or 0), 0),
        (RevenueEventType.LEAD, int(row.get("leads") or 0), 0),
        (RevenueEventType.CUSTOMER, int(row.get("customers") or 0), 0),
        (
            RevenueEventType.REVENUE,
            1 if row.get("revenue_cents") else 0,
            int(row.get("revenue_cents") or 0),
        ),
    )


def _upsert_connector_event(
    db,
    *,
    connector: AnalyticsConnector,
    row: dict,
    event_type: RevenueEventType,
    event_count: int,
    amount_cents: int,
    occurred_at,
) -> bool:
    source_url = row.get("source_url")
    channel = normalize_channel(
        connector.provider.value, source_url, row.get("channel")
    )
    external_id = row.get("external_id")
    key = event_dedupe_key(
        tenant_id=connector.tenant_id,
        provider=connector.provider.value,
        event_type=event_type.value,
        content_piece_id=None,
        source_url=source_url,
        occurred_at=occurred_at,
        external_id=external_id,
    )
    event = (
        db.query(RevenueEvent)
        .filter(
            RevenueEvent.tenant_id == connector.tenant_id,
            RevenueEvent.dedupe_key == key,
            RevenueEvent.is_deleted.is_(False),
        )
        .one_or_none()
    )
    metadata = {
        "provider": connector.provider.value,
        "channel": channel,
        "connector_id": str(connector.id),
        **({"external_id": external_id} if external_id else {}),
        **(row.get("metadata") or {}),
    }
    if event:
        event.owner_id = connector.owner_id
        event.event_count = event_count
        event.amount_cents = amount_cents
        event.currency = row.get("currency") or "USD"
        event.provider = connector.provider.value
        event.channel = channel
        event.source_url = source_url
        event.occurred_at = occurred_at
        event.metadata_json = metadata
        return False
    db.add(
        RevenueEvent(
            tenant_id=connector.tenant_id,
            owner_id=connector.owner_id,
            content_piece_id=None,
            event_type=event_type,
            event_count=event_count,
            amount_cents=amount_cents,
            currency=row.get("currency") or "USD",
            provider=connector.provider.value,
            channel=channel,
            dedupe_key=key,
            source_url=source_url,
            occurred_at=occurred_at,
            metadata_json=metadata,
        )
    )
    return True


def _refresh_connector_oauth(metadata: dict) -> dict:
    oauth = dict(metadata.get("oauth") or {})
    refresh_token = oauth.get("refresh_token")
    if not refresh_token:
        return metadata
    if not (settings.GOOGLE_OAUTH_CLIENT_ID and settings.GOOGLE_OAUTH_CLIENT_SECRET):
        return metadata
    token = _run(
        refresh_google_access_token(
            client_id=settings.GOOGLE_OAUTH_CLIENT_ID,
            client_secret=settings.GOOGLE_OAUTH_CLIENT_SECRET,
            refresh_token=refresh_token,
        )
    )
    oauth["access_token"] = token["access_token"]
    oauth["expires_in"] = token.get("expires_in")
    oauth["token_type"] = token.get("token_type", oauth.get("token_type"))
    oauth["scope"] = token.get("scope", oauth.get("scope"))
    oauth["last_refreshed_at"] = datetime.now(timezone.utc).isoformat()
    metadata["oauth"] = oauth
    return metadata


# -----------------------------------------------------------------------------
# Analytics connector sync (cpu_light queue)
# -----------------------------------------------------------------------------
@celery.task(name="app.workers.tasks.sync_connected_analytics_connectors")
def sync_connected_analytics_connectors() -> str:
    with _SyncSession() as db:
        connectors = (
            db.query(AnalyticsConnector.id)
            .filter(
                AnalyticsConnector.status == AnalyticsConnectorStatus.CONNECTED,
                AnalyticsConnector.is_deleted.is_(False),
            )
            .all()
        )
    for (connector_id,) in connectors:
        sync_analytics_connector.delay(str(connector_id))
    return f"queued:{len(connectors)}"


@celery.task(name="app.workers.tasks.sync_analytics_connector")
def sync_analytics_connector(connector_id: str) -> str:
    """Run one connector sync attempt.

    The provider API fetch/mapping lands in the next slice; this task owns the
    durable state transition so UI/API can safely trigger and observe syncs.
    """
    with _SyncSession() as db:
        connector = db.get(AnalyticsConnector, UUID(connector_id))
        if not connector or connector.is_deleted:
            return "missing"
        if connector.status != AnalyticsConnectorStatus.CONNECTED:
            return "skip"
        connector.status = AnalyticsConnectorStatus.SYNCING
        connector.last_sync_error = None
        db.commit()

        try:
            metadata = dict(connector.metadata_json or {})
            metadata = _refresh_connector_oauth(metadata)
            oauth = metadata.get("oauth") or {}
            if not oauth.get("access_token"):
                raise RuntimeError("missing_oauth_access_token")
            start, end = default_sync_window()
            if connector.provider == AnalyticsConnectorProvider.GSC:
                if not connector.site_url:
                    raise RuntimeError("missing_gsc_site_url")
                rows = _run(
                    fetch_gsc_rows(
                        access_token=oauth["access_token"],
                        site_url=connector.site_url,
                        start=start,
                        end=end,
                    )
                )
            elif connector.provider == AnalyticsConnectorProvider.GA4:
                if not connector.external_property_id:
                    raise RuntimeError("missing_ga4_property_id")
                rows = _run(
                    fetch_ga4_rows(
                        access_token=oauth["access_token"],
                        property_id=connector.external_property_id,
                        site_url=connector.site_url,
                        start=start,
                        end=end,
                    )
                )
            else:
                raise RuntimeError("unsupported_provider")

            imported = 0
            occurred_at = datetime.combine(
                end, datetime.min.time(), tzinfo=timezone.utc
            )
            for row in rows:
                for event_type, event_count, amount_cents in _connector_row_events(row):
                    if event_count:
                        created = _upsert_connector_event(
                            db,
                            connector=connector,
                            row=row,
                            event_type=event_type,
                            event_count=event_count,
                            amount_cents=amount_cents,
                            occurred_at=occurred_at,
                        )
                        if created:
                            imported += 1
            sync = dict(metadata.get("sync") or {})
            sync["last_attempt"] = "provider_fetch_complete"
            sync["last_window"] = {
                "start": start.isoformat(),
                "end": end.isoformat(),
            }
            sync["last_imported_events"] = imported
            sync["last_rows"] = len(rows)
            metadata["sync"] = sync
            connector.metadata_json = metadata
            connector.last_sync_at = datetime.now(timezone.utc)
            connector.status = AnalyticsConnectorStatus.CONNECTED
            db.commit()
            return "queued_provider_fetch"
        except Exception as e:
            connector.status = AnalyticsConnectorStatus.ERROR
            connector.last_sync_error = f"{e.__class__.__name__}: {e}"[:500]
            db.commit()
            return "failed"


# -----------------------------------------------------------------------------
# Brand DNA extraction (cpu_light queue)
# -----------------------------------------------------------------------------
def _parse_profile_json(raw: str) -> dict:
    """Best-effort parse of the model's JSON profile (tolerates fences/prose)."""
    text = re.sub(r"^```(?:json)?|```$", "", raw.strip(), flags=re.MULTILINE).strip()
    try:
        obj = json.loads(text)
        if isinstance(obj, dict):
            return obj
    except Exception:
        pass
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end > start:
        try:
            obj = json.loads(text[start : end + 1])
            if isinstance(obj, dict):
                return obj
        except Exception:
            pass
    return {"extraction_notes": raw[:2000]}


_BRAND_SYSTEM = (
    "You extract a brand profile from website text. Respond with ONLY a JSON "
    "object with keys: tone (string), palette (array of hex color strings), "
    "tagline (string), audience (string), pains (array of strings), "
    "do_phrases (array of strings), dont_phrases (array of strings). "
    "Use empty values when unknown. No prose, no code fences."
)


@celery.task(
    bind=True,
    name="app.workers.tasks.build_brand_profile",
    max_retries=1,
    default_retry_delay=20,
)
def build_brand_profile(self, brand_id: str) -> str:
    with _SyncSession() as db:
        brand = db.get(Brand, UUID(brand_id))
        if not brand:
            return "missing"
        if not brand.source_url:
            brand.status = BrandStatus.READY
            brand.profile = brand.profile or {}
            db.commit()
            return "no_url"

        brand.status = BrandStatus.SCRAPING
        db.commit()
        try:
            site = fetch_site(brand.source_url)
        except UnsafeURLError as e:
            brand.status = BrandStatus.FAILED
            brand.error_message = f"unsafe url: {e}"[:500]
            db.commit()
            return "unsafe"
        except Exception as e:
            brand.status = BrandStatus.FAILED
            brand.error_message = f"fetch failed: {e.__class__.__name__}"[:500]
            db.commit()
            return "fetch_failed"

        brand.status = BrandStatus.EXTRACTING
        db.commit()
        user_msg = (
            f"Title: {site.get('title')}\n"
            f"Description: {site.get('description')}\n\n"
            f"Website text:\n{site.get('text', '')}"
        )
        try:
            raw, _resp = _run(
                chat_completion(
                    messages=[
                        {"role": "system", "content": _BRAND_SYSTEM},
                        {"role": "user", "content": user_msg},
                    ],
                    model=settings.DEFAULT_LLM_MODEL,
                    temperature=0.2,
                )
            )
        except Exception as e:
            brand.status = BrandStatus.FAILED
            brand.error_message = f"extract failed: {e.__class__.__name__}"[:500]
            db.commit()
            raise self.retry(exc=e)

        profile = _parse_profile_json(raw)
        if site.get("theme_color") and not profile.get("palette"):
            profile["palette"] = [site["theme_color"]]
        profile.setdefault("source_title", site.get("title"))
        brand.profile = profile
        brand.status = BrandStatus.READY
        db.commit()
    return "ok"


# -----------------------------------------------------------------------------
# Scheduled content publish (content calendar closing the loop: due_at +
# a pre-configured scheduled_publish target auto-publishes without a manual
# click). Same "sweep + fan out" shape as sync_connected_analytics_connectors.
# -----------------------------------------------------------------------------
def _sweep_due_content(db) -> list:
    """Query logic isolated from the Celery task + its module-level engine,
    so tests can pass in the test session directly (mirrors
    app.core.orchestrator.execute_run's db-argument shape)."""
    now = datetime.now(timezone.utc).isoformat()
    return (
        db.query(ContentPiece.id)
        .filter(
            ContentPiece.status == ContentStatus.APPROVED,
            ContentPiece.is_deleted.is_(False),
            ContentPiece.metadata_json["due_at"].astext <= now,
            ContentPiece.metadata_json["scheduled_publish"].isnot(None),
        )
        .all()
    )


@celery.task(name="app.workers.tasks.publish_due_content")
def publish_due_content() -> str:
    with _SyncSession() as db:
        candidates = _sweep_due_content(db)
    for (cp_id,) in candidates:
        publish_scheduled_content_piece.delay(str(cp_id))
    return f"queued:{len(candidates)}"


def _resolve_github_token_sync(db, tenant_id: UUID) -> str | None:
    credential = (
        db.query(GitHubCredential)
        .filter(
            GitHubCredential.tenant_id == tenant_id,
            GitHubCredential.is_deleted.is_(False),
        )
        .order_by(GitHubCredential.updated_at.desc())
        .first()
    )
    if credential:
        try:
            return decrypt_secret(credential.token_encrypted)
        except CredentialCryptoError:
            return None
    return settings.GITHUB_TOKEN or None


def _render_scheduled_markdown(cp: ContentPiece) -> str:
    """Same frontmatter shape as app.routers.content._render_markdown —
    duplicated rather than imported (that helper lives in an async-router
    module with FastAPI-only deps; both are pure functions over a
    ContentPiece with no I/O, and the router version is what a manual
    /publish call renders, so keeping them in obvious lockstep in one
    review is safer than an import that couples a worker to a router
    module's import graph for a handful of lines)."""

    def esc(v: str) -> str:
        return str(v).replace("\\", "\\\\").replace('"', '\\"')

    article = ((cp.metadata_json or {}).get("article")) or {}
    date = cp.created_at.date().isoformat()
    lines = ["---", f'title: "{esc(cp.title)}"']
    if (cp.format or "") == "blog_post":
        slug = re.sub(r"-{2,}", "-", re.sub(r"[^a-z0-9 _/-]", "", cp.title.lower()))
        slug = slug.replace(" ", "-").replace("_", "-").replace("/", "-").strip("-")
        slug = (article.get("slug") or slug) or "untitled"
        description = article.get("description") or ""
        tags = article.get("tags") or []
        lines += [
            f"slug: {slug}",
            f"date: {date}",
            f'description: "{esc(description)}"',
            "tags: [" + ", ".join(f'"{esc(t)}"' for t in tags) + "]",
            "draft: false",  # only APPROVED pieces reach this task
        ]
    else:
        lines.append(f"date: {date}")
    lines += ["---", "", ""]
    return "\n".join(lines) + (cp.body or "")


def _publish_scheduled_content_piece(db, content_piece_id: str) -> str:
    """Core logic, isolated from the Celery task wrapper so tests can pass
    in the test session directly (same split as _sweep_due_content above)."""
    cp = db.get(ContentPiece, UUID(content_piece_id))
    if not cp or cp.is_deleted:
        return "missing"
    if cp.status != ContentStatus.APPROVED:
        return "skipped:not_approved"  # edited/transitioned since the sweep
    scheduled = (cp.metadata_json or {}).get("scheduled_publish")
    if not scheduled:
        return "skipped:not_scheduled"  # cleared since the sweep

    channel = scheduled["channel"]
    config = scheduled.get("config") or {}
    body = _render_scheduled_markdown(cp)

    try:
        channel_enum = PublicationChannel(channel)
    except ValueError:
        return f"failed:unknown_channel:{channel}"

    pub = Publication(
        tenant_id=cp.tenant_id,
        owner_id=cp.owner_id,
        content_piece_id=cp.id,
        channel=channel_enum,
        status=PublicationStatus.PUBLISHING,
        target={"channel": channel},
    )
    db.add(pub)
    db.commit()
    db.refresh(pub)

    try:
        if channel == "GITHUB_PR":
            token = _resolve_github_token_sync(db, cp.tenant_id)
            if not token:
                raise PublisherError("GitHub publishing not configured")
            from app.core.github_publisher import publish_markdown

            path = config.get("path") or f"content/{cp.id}.md"
            branch = config.get("branch") or f"opengrow/{cp.id}"
            result = _run(
                publish_markdown(
                    repo=config["repo"],
                    path=path,
                    content=body,
                    branch=branch,
                    commit_message=config.get("commit_message")
                    or f"content: {cp.title}",
                    pr_title=config.get("pr_title") or cp.title,
                    pr_body=config.get("pr_body")
                    or f"Published via OpenGrow — content piece {cp.id}.",
                    base_branch=config.get("base_branch"),
                    token=token,
                    draft=config.get("draft", False),
                    labels=config.get("labels"),
                    reviewers=config.get("reviewers"),
                )
            )
            pub.status = PublicationStatus.PR_OPENED
            pub.url = result["pr_url"]
            pub.external_ref = f"PR #{result['pr_number']} ({result['branch']})"
        else:
            adapter = get_adapter(channel)
            if adapter is None:
                raise PublisherError(f"{channel} publishing not implemented")
            result = _run(adapter.publish(title=cp.title, body=body, config=config))
            pub.status = PublicationStatus.PUBLISHED
            pub.url = result["url"]
            pub.external_ref = result["external_ref"]
    except (PublisherError, GitHubPublishError, KeyError) as e:
        pub.status = PublicationStatus.FAILED
        pub.error_message = str(e)[:500]
        db.commit()
        return f"failed:{e.__class__.__name__}"

    cp.status = ContentStatus.PUBLISHED
    db.commit()
    record_usage_sync(
        db,
        tenant_id=cp.tenant_id,
        kind="publish",
        ref_type="publication",
        ref_id=str(pub.id),
        details={"channel": channel, "scheduled": True},
    )
    return "ok"


@celery.task(
    bind=True,
    name="app.workers.tasks.publish_scheduled_content_piece",
    max_retries=2,
    default_retry_delay=60,
)
def publish_scheduled_content_piece(self, content_piece_id: str) -> str:
    with _SyncSession() as db:
        return _publish_scheduled_content_piece(db, content_piece_id)


# -----------------------------------------------------------------------------
# Attribution loop: decay/growth recommendations (content calendar's "what to
# write/refresh next" — closes Phase 6). Sync twin of app.routers.analytics'
# _content_counts_for_period (that helper is async-only, and this codebase's
# convention is sync Session + sync ORM queries inside Celery tasks, same as
# every other _sync-suffixed helper here).
# -----------------------------------------------------------------------------
RECOMMENDATION_WINDOW_DAYS = 30


def _content_counts_for_period_sync(
    db, tenant_id: UUID, *, start: datetime, end: datetime
) -> dict[UUID, dict[str, int]]:
    rows = (
        db.query(RevenueEvent)
        .filter(
            RevenueEvent.tenant_id == tenant_id,
            RevenueEvent.content_piece_id.isnot(None),
            RevenueEvent.is_deleted.is_(False),
            RevenueEvent.occurred_at >= start,
            RevenueEvent.occurred_at < end,
        )
        .all()
    )
    by_content: dict[UUID, dict[str, int]] = {}
    for event in rows:
        counts = by_content.setdefault(
            event.content_piece_id,
            {
                "events": 0,
                "visits": 0,
                "signups": 0,
                "leads": 0,
                "customers": 0,
                "revenue_cents": 0,
            },
        )
        event_count = event.event_count or 1
        counts["events"] += event_count
        if event.event_type == RevenueEventType.REVENUE:
            counts["revenue_cents"] += event.amount_cents
    return by_content


def _generate_recommendations_for_tenant(db, tenant_id: UUID) -> int:
    """Core logic, isolated from the Celery task wrapper so tests can pass
    in the test session directly (same split as the scheduled-publish
    tasks above)."""
    previous_start, current_start, end = analytics_periods(RECOMMENDATION_WINDOW_DAYS)
    current_counts = _content_counts_for_period_sync(
        db, tenant_id, start=current_start, end=end
    )
    previous_counts = _content_counts_for_period_sync(
        db, tenant_id, start=previous_start, end=current_start
    )

    published = (
        db.query(ContentPiece)
        .filter(
            ContentPiece.tenant_id == tenant_id,
            ContentPiece.status == ContentStatus.PUBLISHED,
            ContentPiece.is_deleted.is_(False),
        )
        .all()
    )
    pieces = [{"id": cp.id, "title": cp.title} for cp in published]
    suggestions = build_recommendations(
        pieces, current_counts=current_counts, previous_counts=previous_counts
    )

    # Skip a suggestion if an open (PENDING) one for the same piece+kind
    # already exists — the partial unique index would reject the insert
    # anyway, but checking first avoids a noisy IntegrityError per sweep.
    existing_pending = {
        (row.content_piece_id, row.kind)
        for row in db.query(
            ContentRecommendation.content_piece_id, ContentRecommendation.kind
        ).filter(
            ContentRecommendation.tenant_id == tenant_id,
            ContentRecommendation.status == ContentRecommendationStatus.PENDING,
            ContentRecommendation.is_deleted.is_(False),
        )
    }

    created = 0
    for s in suggestions:
        kind = ContentRecommendationKind(s["kind"])
        if (s["content_piece_id"], kind) in existing_pending:
            continue
        db.add(
            ContentRecommendation(
                id=uuid4(),
                tenant_id=tenant_id,
                kind=kind,
                content_piece_id=s["content_piece_id"],
                title=s["title"],
                rationale=s["rationale"],
                score=s["score"],
            )
        )
        created += 1
    if created:
        db.commit()
    return created


@celery.task(name="app.workers.tasks.generate_content_recommendations")
def generate_content_recommendations() -> str:
    with _SyncSession() as db:
        tenant_ids = [row[0] for row in db.query(Tenant.id).all()]
        total = 0
        for tenant_id in tenant_ids:
            total += _generate_recommendations_for_tenant(db, tenant_id)
    return f"created:{total}"
