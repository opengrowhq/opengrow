"""Integration tests for the recommendations router: list/dismiss/start-run."""

import uuid

from app.models.content_piece import ContentPiece, ContentStatus
from app.models.content_recommendation import (
    ContentRecommendation,
    ContentRecommendationKind,
)


async def _seed_recommendation(
    db, tenant, user, *, kind=ContentRecommendationKind.REFRESH, content_piece_id=None
):
    rec = ContentRecommendation(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        kind=kind,
        content_piece_id=content_piece_id,
        title="Refresh \"Old post\"",
        rationale="traffic dropped 80%",
        score=0.8,
    )
    db.add(rec)
    await db.commit()
    await db.refresh(rec)
    return rec


async def _seed_content_piece(db, tenant, user, **article_fields):
    cp = ContentPiece(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        owner_id=user.id,
        title="Old post",
        body="body",
        status=ContentStatus.PUBLISHED,
        metadata_json={"article": article_fields} if article_fields else None,
    )
    db.add(cp)
    await db.commit()
    await db.refresh(cp)
    return cp


async def test_list_recommendations_defaults_to_pending(client, db, tenant_factory):
    acct = await tenant_factory()
    rec = await _seed_recommendation(db, acct["tenant"], acct["user"])

    resp = await client.get("/analytics/recommendations", headers=acct["headers"])

    assert resp.status_code == 200
    ids = [r["id"] for r in resp.json()]
    assert str(rec.id) in ids


async def test_list_recommendations_filters_by_status(client, db, tenant_factory):
    acct = await tenant_factory()
    await _seed_recommendation(db, acct["tenant"], acct["user"])

    resp = await client.get(
        "/analytics/recommendations",
        params={"status": "DISMISSED"},
        headers=acct["headers"],
    )

    assert resp.status_code == 200
    assert resp.json() == []


async def test_list_recommendations_rejects_unknown_status(client, tenant_factory):
    acct = await tenant_factory()
    resp = await client.get(
        "/analytics/recommendations",
        params={"status": "NOT_A_STATUS"},
        headers=acct["headers"],
    )
    assert resp.status_code == 400


async def test_list_recommendations_is_tenant_scoped(client, db, tenant_factory):
    a = await tenant_factory()
    b = await tenant_factory()
    await _seed_recommendation(db, a["tenant"], a["user"])

    resp = await client.get("/analytics/recommendations", headers=b["headers"])

    assert resp.status_code == 200
    assert resp.json() == []


async def test_dismiss_recommendation(client, db, tenant_factory):
    acct = await tenant_factory()
    rec = await _seed_recommendation(db, acct["tenant"], acct["user"])

    resp = await client.post(
        f"/analytics/recommendations/{rec.id}/dismiss", headers=acct["headers"]
    )

    assert resp.status_code == 200
    assert resp.json()["status"] == "DISMISSED"


async def test_dismiss_already_dismissed_recommendation_conflicts(
    client, db, tenant_factory
):
    acct = await tenant_factory()
    rec = await _seed_recommendation(db, acct["tenant"], acct["user"])
    await client.post(
        f"/analytics/recommendations/{rec.id}/dismiss", headers=acct["headers"]
    )

    resp = await client.post(
        f"/analytics/recommendations/{rec.id}/dismiss", headers=acct["headers"]
    )

    assert resp.status_code == 409


async def test_dismiss_missing_recommendation_404s(client, tenant_factory):
    acct = await tenant_factory()
    resp = await client.post(
        f"/analytics/recommendations/{uuid.uuid4()}/dismiss", headers=acct["headers"]
    )
    assert resp.status_code == 404


async def test_start_run_from_refresh_recommendation(
    client, db, tenant_factory, no_celery
):
    acct = await tenant_factory()
    cp = await _seed_content_piece(
        db,
        acct["tenant"],
        acct["user"],
        primary_keyword="founder blogging",
        tags=["seo"],
    )
    rec = await _seed_recommendation(
        db, acct["tenant"], acct["user"], content_piece_id=cp.id
    )

    resp = await client.post(
        f"/analytics/recommendations/{rec.id}/start-run", headers=acct["headers"]
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ACTIONED"
    assert body["orchestrator_run_id"]

    run = await client.get(
        f"/orchestrator/runs/{body['orchestrator_run_id']}", headers=acct["headers"]
    )
    assert run.status_code == 200
    assert "Old post" in run.json()["brief"]


async def test_start_run_without_content_piece_uses_recommendation_title(
    client, db, tenant_factory, no_celery
):
    acct = await tenant_factory()
    rec = await _seed_recommendation(db, acct["tenant"], acct["user"])

    resp = await client.post(
        f"/analytics/recommendations/{rec.id}/start-run", headers=acct["headers"]
    )

    assert resp.status_code == 200
    assert resp.json()["status"] == "ACTIONED"


async def test_start_run_twice_conflicts(client, db, tenant_factory, no_celery):
    acct = await tenant_factory()
    rec = await _seed_recommendation(db, acct["tenant"], acct["user"])
    await client.post(
        f"/analytics/recommendations/{rec.id}/start-run", headers=acct["headers"]
    )

    resp = await client.post(
        f"/analytics/recommendations/{rec.id}/start-run", headers=acct["headers"]
    )

    assert resp.status_code == 409


async def test_recommendations_require_auth(client):
    assert (await client.get("/analytics/recommendations")).status_code == 401
