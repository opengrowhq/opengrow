"""Tests for the attribution-loop sweep task
(app.workers.tasks.generate_content_recommendations / _generate_recommendations_for_tenant)."""

import uuid
from datetime import datetime, timedelta, timezone

from app.models.analytics import RevenueEvent, RevenueEventType
from app.models.content_piece import ContentPiece, ContentStatus
from app.models.content_recommendation import (
    ContentRecommendation,
    ContentRecommendationKind,
    ContentRecommendationStatus,
)
from app.models.tenant import Tenant
from app.models.user import User
from app.workers import tasks


def _seed_tenant_user(sync_db):
    tenant = Tenant(id=uuid.uuid4(), slug=f"rec-{uuid.uuid4().hex[:8]}", name="T")
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


def _seed_published_piece(sync_db, tenant, user, title="Old post", tags=None):
    cp = ContentPiece(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        owner_id=user.id,
        title=title,
        body="body",
        status=ContentStatus.PUBLISHED,
        metadata_json={"article": {"tags": tags}} if tags else None,
    )
    sync_db.add(cp)
    sync_db.commit()
    return cp


def _seed_events(sync_db, tenant, user, cp, *, count, days_ago):
    occurred = datetime.now(timezone.utc) - timedelta(days=days_ago)
    for _ in range(count):
        sync_db.add(
            RevenueEvent(
                id=uuid.uuid4(),
                tenant_id=tenant.id,
                owner_id=user.id,
                content_piece_id=cp.id,
                event_type=RevenueEventType.VISIT,
                event_count=1,
                occurred_at=occurred,
            )
        )
    sync_db.commit()


def test_generates_refresh_recommendation_for_decaying_piece(sync_db):
    tenant, user = _seed_tenant_user(sync_db)
    cp = _seed_published_piece(sync_db, tenant, user)
    _seed_events(sync_db, tenant, user, cp, count=100, days_ago=45)  # previous window
    _seed_events(sync_db, tenant, user, cp, count=5, days_ago=5)  # current window

    created = tasks._generate_recommendations_for_tenant(sync_db, tenant.id)

    assert created == 1
    rec = (
        sync_db.query(ContentRecommendation)
        .filter(ContentRecommendation.tenant_id == tenant.id)
        .one()
    )
    assert rec.kind == ContentRecommendationKind.REFRESH
    assert rec.content_piece_id == cp.id
    assert rec.status == ContentRecommendationStatus.PENDING
    assert cp.title in rec.title


def test_generates_double_down_recommendation_for_growing_piece(sync_db):
    tenant, user = _seed_tenant_user(sync_db)
    cp = _seed_published_piece(sync_db, tenant, user, title="Hot post")
    _seed_events(sync_db, tenant, user, cp, count=100, days_ago=45)
    _seed_events(sync_db, tenant, user, cp, count=500, days_ago=5)

    created = tasks._generate_recommendations_for_tenant(sync_db, tenant.id)

    assert created == 1
    rec = (
        sync_db.query(ContentRecommendation)
        .filter(ContentRecommendation.tenant_id == tenant.id)
        .one()
    )
    assert rec.kind == ContentRecommendationKind.DOUBLE_DOWN


def test_no_recommendation_for_flat_piece(sync_db):
    tenant, user = _seed_tenant_user(sync_db)
    cp = _seed_published_piece(sync_db, tenant, user)
    _seed_events(sync_db, tenant, user, cp, count=50, days_ago=45)
    _seed_events(sync_db, tenant, user, cp, count=52, days_ago=5)

    created = tasks._generate_recommendations_for_tenant(sync_db, tenant.id)

    assert created == 0


def test_no_recommendation_for_draft_piece_even_if_decaying(sync_db):
    tenant, user = _seed_tenant_user(sync_db)
    cp = ContentPiece(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        owner_id=user.id,
        title="Draft post",
        body="body",
        status=ContentStatus.DRAFT,
    )
    sync_db.add(cp)
    sync_db.commit()
    _seed_events(sync_db, tenant, user, cp, count=100, days_ago=45)
    _seed_events(sync_db, tenant, user, cp, count=5, days_ago=5)

    created = tasks._generate_recommendations_for_tenant(sync_db, tenant.id)

    assert created == 0


def test_does_not_duplicate_pending_recommendation_on_repeat_sweep(sync_db):
    tenant, user = _seed_tenant_user(sync_db)
    cp = _seed_published_piece(sync_db, tenant, user)
    _seed_events(sync_db, tenant, user, cp, count=100, days_ago=45)
    _seed_events(sync_db, tenant, user, cp, count=5, days_ago=5)

    first = tasks._generate_recommendations_for_tenant(sync_db, tenant.id)
    second = tasks._generate_recommendations_for_tenant(sync_db, tenant.id)

    assert first == 1
    assert second == 0
    count = (
        sync_db.query(ContentRecommendation)
        .filter(ContentRecommendation.tenant_id == tenant.id)
        .count()
    )
    assert count == 1


def test_generates_new_recommendation_after_prior_one_dismissed(sync_db):
    tenant, user = _seed_tenant_user(sync_db)
    cp = _seed_published_piece(sync_db, tenant, user)
    _seed_events(sync_db, tenant, user, cp, count=100, days_ago=45)
    _seed_events(sync_db, tenant, user, cp, count=5, days_ago=5)

    tasks._generate_recommendations_for_tenant(sync_db, tenant.id)
    rec = (
        sync_db.query(ContentRecommendation)
        .filter(ContentRecommendation.tenant_id == tenant.id)
        .one()
    )
    rec.status = ContentRecommendationStatus.DISMISSED
    sync_db.commit()

    created = tasks._generate_recommendations_for_tenant(sync_db, tenant.id)

    assert created == 1
    count = (
        sync_db.query(ContentRecommendation)
        .filter(ContentRecommendation.tenant_id == tenant.id)
        .count()
    )
    assert count == 2


def test_generates_new_topic_recommendation_from_tag_gap(sync_db):
    tenant, user = _seed_tenant_user(sync_db)
    _seed_published_piece(sync_db, tenant, user, "A", tags=["seo", "onboarding"])
    _seed_published_piece(sync_db, tenant, user, "B", tags=["seo", "onboarding"])
    _seed_published_piece(sync_db, tenant, user, "C", tags=["pricing"])

    created = tasks._generate_recommendations_for_tenant(sync_db, tenant.id)

    assert created == 1
    rec = (
        sync_db.query(ContentRecommendation)
        .filter(ContentRecommendation.tenant_id == tenant.id)
        .one()
    )
    assert rec.kind == ContentRecommendationKind.NEW_TOPIC
    assert rec.content_piece_id is None
    assert "pricing" in rec.title


def test_new_topic_recommendation_not_duplicated_on_repeat_sweep(sync_db):
    tenant, user = _seed_tenant_user(sync_db)
    _seed_published_piece(sync_db, tenant, user, "A", tags=["seo", "onboarding"])
    _seed_published_piece(sync_db, tenant, user, "B", tags=["seo", "onboarding"])
    _seed_published_piece(sync_db, tenant, user, "C", tags=["pricing"])

    first = tasks._generate_recommendations_for_tenant(sync_db, tenant.id)
    second = tasks._generate_recommendations_for_tenant(sync_db, tenant.id)

    assert first == 1
    assert second == 0
    count = (
        sync_db.query(ContentRecommendation)
        .filter(
            ContentRecommendation.tenant_id == tenant.id,
            ContentRecommendation.kind == ContentRecommendationKind.NEW_TOPIC,
        )
        .count()
    )
    assert count == 1


def test_multiple_distinct_new_topic_gaps_all_created(sync_db):
    """Two different gap suggestions (both content_piece_id=None) must not
    collide in the dedup set the way the DB's own partial unique index
    correctly allows — regression test for the title-based dedup fix."""
    tenant, user = _seed_tenant_user(sync_db)
    _seed_published_piece(sync_db, tenant, user, "A", tags=["seo", "onboarding"])
    _seed_published_piece(sync_db, tenant, user, "B", tags=["seo", "onboarding"])
    _seed_published_piece(sync_db, tenant, user, "C", tags=["pricing"])
    _seed_published_piece(sync_db, tenant, user, "D", tags=["billing"])

    created = tasks._generate_recommendations_for_tenant(sync_db, tenant.id)

    assert created == 2
    titles = {
        rec.title
        for rec in sync_db.query(ContentRecommendation).filter(
            ContentRecommendation.tenant_id == tenant.id,
            ContentRecommendation.kind == ContentRecommendationKind.NEW_TOPIC,
        )
    }
    assert len(titles) == 2


def test_sweep_is_scoped_per_tenant(sync_db):
    tenant_a, user_a = _seed_tenant_user(sync_db)
    tenant_b, _user_b = _seed_tenant_user(sync_db)
    cp_a = _seed_published_piece(sync_db, tenant_a, user_a)
    _seed_events(sync_db, tenant_a, user_a, cp_a, count=100, days_ago=45)
    _seed_events(sync_db, tenant_a, user_a, cp_a, count=5, days_ago=5)

    created_b = tasks._generate_recommendations_for_tenant(sync_db, tenant_b.id)

    assert created_b == 0
