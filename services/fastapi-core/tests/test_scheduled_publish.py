"""Tests for the content-calendar scheduled publish tasks: the sweep query
(publish_due_content) and the per-piece publish (publish_scheduled_content_piece)."""

import uuid
from datetime import datetime, timedelta, timezone

from app.models.content_piece import ContentPiece, ContentStatus
from app.models.publication import Publication, PublicationStatus
from app.models.tenant import Tenant
from app.models.user import User
from app.workers import tasks


def _seed_tenant_user(sync_db):
    tenant = Tenant(id=uuid.uuid4(), slug=f"sched-{uuid.uuid4().hex[:8]}", name="T")
    sync_db.add(tenant)
    sync_db.commit()
    user = User(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        email=f"{uuid.uuid4().hex[:8]}@ex.com",
        password_hash="x",
        display_name="U",
    )
    sync_db.add(user)
    sync_db.commit()
    return tenant, user


def _seed_content_piece(
    sync_db,
    tenant,
    user,
    *,
    status=ContentStatus.APPROVED,
    due_at=None,
    scheduled_publish=None,
    format=None,
):
    metadata = {}
    if due_at is not None:
        metadata["due_at"] = due_at.isoformat() if hasattr(due_at, "isoformat") else due_at
    if scheduled_publish is not None:
        metadata["scheduled_publish"] = scheduled_publish
    cp = ContentPiece(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        owner_id=user.id,
        title="Why founders should blog",
        body="body text",
        format=format,
        status=status,
        metadata_json=metadata or None,
    )
    sync_db.add(cp)
    sync_db.commit()
    return cp


PAST = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
FUTURE = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()


def test_publish_due_content_dispatches_only_eligible_pieces(sync_db, monkeypatch):
    tenant, user = _seed_tenant_user(sync_db)
    dispatched = []
    monkeypatch.setattr(
        tasks.publish_scheduled_content_piece,
        "delay",
        lambda cp_id: dispatched.append(cp_id),
    )

    eligible = _seed_content_piece(
        sync_db,
        tenant,
        user,
        due_at=PAST,
        scheduled_publish={"channel": "SLACK", "config": {}},
    )
    # not due yet
    _seed_content_piece(
        sync_db,
        tenant,
        user,
        due_at=FUTURE,
        scheduled_publish={"channel": "SLACK", "config": {}},
    )
    # due but not scheduled
    _seed_content_piece(sync_db, tenant, user, due_at=PAST)
    # due + scheduled but not APPROVED
    _seed_content_piece(
        sync_db,
        tenant,
        user,
        status=ContentStatus.DRAFT,
        due_at=PAST,
        scheduled_publish={"channel": "SLACK", "config": {}},
    )

    candidates = tasks._sweep_due_content(sync_db)
    for (cp_id,) in candidates:
        tasks.publish_scheduled_content_piece.delay(str(cp_id))
    result = f"queued:{len(candidates)}"

    assert result == "queued:1"
    assert dispatched == [str(eligible.id)]


def test_publish_scheduled_content_piece_generic_channel_success(
    sync_db, monkeypatch
):
    tenant, user = _seed_tenant_user(sync_db)
    cp = _seed_content_piece(
        sync_db,
        tenant,
        user,
        due_at=PAST,
        scheduled_publish={"channel": "SLACK", "config": {"webhook_url": "https://x"}},
    )

    class _FakeAdapter:
        async def publish(self, *, title, body, config):
            assert config == {"webhook_url": "https://x"}
            return {"url": "https://slack.com/x", "external_ref": "msg-1"}

    monkeypatch.setattr(tasks, "get_adapter", lambda channel: _FakeAdapter())

    result = tasks._publish_scheduled_content_piece(sync_db, str(cp.id))

    assert result == "ok"
    sync_db.refresh(cp)
    assert cp.status == ContentStatus.PUBLISHED
    pub = sync_db.query(Publication).filter(Publication.content_piece_id == cp.id).one()
    assert pub.status == PublicationStatus.PUBLISHED
    assert pub.url == "https://slack.com/x"


def test_publish_scheduled_content_piece_github_success(sync_db, monkeypatch):
    tenant, user = _seed_tenant_user(sync_db)
    cp = _seed_content_piece(
        sync_db,
        tenant,
        user,
        due_at=PAST,
        scheduled_publish={"channel": "GITHUB_PR", "config": {"repo": "acme/blog"}},
        format="blog_post",
    )

    async def fake_publish_markdown(**kwargs):
        assert kwargs["repo"] == "acme/blog"
        return {"pr_url": "https://github.com/x/pull/1", "pr_number": 1, "branch": "b"}

    monkeypatch.setattr(
        "app.core.github_publisher.publish_markdown", fake_publish_markdown
    )
    monkeypatch.setattr(tasks, "_resolve_github_token_sync", lambda db, tid: "ghp_x")

    result = tasks._publish_scheduled_content_piece(sync_db, str(cp.id))

    assert result == "ok"
    sync_db.refresh(cp)
    assert cp.status == ContentStatus.PUBLISHED
    pub = sync_db.query(Publication).filter(Publication.content_piece_id == cp.id).one()
    assert pub.external_ref == "PR #1 (b)"


def test_publish_scheduled_content_piece_github_missing_token_fails_cleanly(
    sync_db, monkeypatch
):
    tenant, user = _seed_tenant_user(sync_db)
    cp = _seed_content_piece(
        sync_db,
        tenant,
        user,
        due_at=PAST,
        scheduled_publish={"channel": "GITHUB_PR", "config": {"repo": "acme/blog"}},
    )
    monkeypatch.setattr(tasks, "_resolve_github_token_sync", lambda db, tid: None)

    result = tasks._publish_scheduled_content_piece(sync_db, str(cp.id))

    assert result == "failed:PublisherError"
    sync_db.refresh(cp)
    assert cp.status == ContentStatus.APPROVED  # never marked published
    pub = sync_db.query(Publication).filter(Publication.content_piece_id == cp.id).one()
    assert pub.status == PublicationStatus.FAILED


def test_publish_scheduled_content_piece_skips_if_no_longer_approved(sync_db):
    tenant, user = _seed_tenant_user(sync_db)
    cp = _seed_content_piece(
        sync_db,
        tenant,
        user,
        status=ContentStatus.DRAFT,
        due_at=PAST,
        scheduled_publish={"channel": "SLACK", "config": {}},
    )

    result = tasks._publish_scheduled_content_piece(sync_db, str(cp.id))

    assert result == "skipped:not_approved"


def test_publish_scheduled_content_piece_skips_if_scheduling_was_cleared(sync_db):
    tenant, user = _seed_tenant_user(sync_db)
    cp = _seed_content_piece(sync_db, tenant, user, due_at=PAST)

    result = tasks._publish_scheduled_content_piece(sync_db, str(cp.id))

    assert result == "skipped:not_scheduled"


def test_publish_scheduled_content_piece_missing_row(sync_db):
    result = tasks._publish_scheduled_content_piece(sync_db, str(uuid.uuid4()))
    assert result == "missing"


def test_publish_scheduled_content_piece_adapter_failure_marks_publication_failed(
    sync_db, monkeypatch
):
    tenant, user = _seed_tenant_user(sync_db)
    cp = _seed_content_piece(
        sync_db,
        tenant,
        user,
        due_at=PAST,
        scheduled_publish={"channel": "SLACK", "config": {}},
    )

    class _FailingAdapter:
        async def publish(self, *, title, body, config):
            from app.core.publishers import PublisherError

            raise PublisherError("webhook rejected")

    monkeypatch.setattr(tasks, "get_adapter", lambda channel: _FailingAdapter())

    result = tasks._publish_scheduled_content_piece(sync_db, str(cp.id))

    assert result == "failed:PublisherError"
    sync_db.refresh(cp)
    assert cp.status == ContentStatus.APPROVED
