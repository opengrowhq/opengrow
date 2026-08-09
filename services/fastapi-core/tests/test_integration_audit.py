"""Integration tests for the security audit trail."""

from datetime import datetime, timedelta, timezone
from urllib.parse import quote
from uuid import uuid4

import pytest

from app.core.audit import record_audit_event
from app.models.audit import AuditLog


async def test_audit_log_model_has_no_mutation_columns():
    """AuditLog must never grow updated_at/is_deleted — that's what makes it
    append-only. This test fails loudly if someone adds TenantMixin later."""
    columns = {c.name for c in AuditLog.__table__.columns}
    assert "updated_at" not in columns
    assert "is_deleted" not in columns
    assert columns == {
        "id",
        "created_at",
        "tenant_id",
        "actor_user_id",
        "actor_email",
        "action",
        "ref_type",
        "ref_id",
        "ip_address",
        "user_agent",
        "details",
    }


async def test_audit_log_row_persists(db, tenant_factory):
    acct = await tenant_factory()
    entry = AuditLog(
        id=uuid4(),
        tenant_id=acct["tenant"].id,
        actor_user_id=acct["user"].id,
        actor_email=acct["email"],
        action="test.event",
        ref_type="thing",
        ref_id="123",
        details={"k": "v"},
    )
    db.add(entry)
    await db.commit()
    await db.refresh(entry)

    fetched = await db.get(AuditLog, entry.id)
    assert fetched.action == "test.event"
    assert fetched.tenant_id == acct["tenant"].id
    assert fetched.created_at is not None


async def test_record_audit_event_defaults_to_no_commit(db, tenant_factory):
    acct = await tenant_factory()
    entry = await record_audit_event(
        db,
        action="test.no_commit",
        tenant_id=acct["tenant"].id,
        actor_user_id=acct["user"].id,
    )
    assert entry.id is not None
    # Visible on the same session even without an explicit commit (flush).
    fetched = await db.get(AuditLog, entry.id)
    assert fetched is not None
    assert fetched.action == "test.no_commit"


async def test_record_audit_event_commit_true_persists_across_sessions(
    db, tenant_factory, engine
):
    from sqlalchemy.ext.asyncio import async_sessionmaker

    acct = await tenant_factory()
    entry = await record_audit_event(
        db,
        action="test.committed",
        tenant_id=acct["tenant"].id,
        actor_email=acct["email"],
        commit=True,
    )

    Session = async_sessionmaker(engine, expire_on_commit=False)
    async with Session() as other_session:
        fetched = await other_session.get(AuditLog, entry.id)
        assert fetched is not None
        assert fetched.actor_email == acct["email"]


async def test_record_audit_event_failure_rolls_back_caller_transaction(
    db, tenant_factory, monkeypatch
):
    """The whole point of commit=False: a failure here must break the
    caller's transaction, not be swallowed."""
    acct = await tenant_factory()

    async def _boom(*args, **kwargs):
        raise RuntimeError("simulated audit failure")

    monkeypatch.setattr(db, "flush", _boom)

    with pytest.raises(RuntimeError, match="simulated audit failure"):
        await record_audit_event(
            db, action="test.will_fail", tenant_id=acct["tenant"].id
        )


async def test_get_audit_requires_auth(client):
    assert (await client.get("/audit")).status_code == 401


async def test_get_audit_returns_own_tenant_rows_paginated(client, db, tenant_factory):
    acct = await tenant_factory()

    for i in range(3):
        await record_audit_event(
            db,
            action=f"test.event.{i}",
            tenant_id=acct["tenant"].id,
            actor_user_id=acct["user"].id,
            commit=True,
        )

    resp = await client.get("/audit", headers=acct["headers"])
    assert resp.status_code == 200
    assert resp.headers["X-Total-Count"] == "3"
    actions = {row["action"] for row in resp.json()}
    assert actions == {"test.event.0", "test.event.1", "test.event.2"}

    page1 = await client.get("/audit?limit=2", headers=acct["headers"])
    assert len(page1.json()) == 2
    assert page1.headers["X-Total-Count"] == "3"


async def test_get_audit_filters_by_action_and_date(client, db, tenant_factory):
    acct = await tenant_factory()
    old = await record_audit_event(
        db, action="auth.login.success", tenant_id=acct["tenant"].id, commit=True
    )
    old.created_at = datetime.now(timezone.utc) - timedelta(days=10)
    await db.commit()
    await record_audit_event(
        db, action="api_key.created", tenant_id=acct["tenant"].id, commit=True
    )

    by_action = await client.get(
        "/audit?action=api_key.created", headers=acct["headers"]
    )
    assert [r["action"] for r in by_action.json()] == ["api_key.created"]

    since = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    recent = await client.get(
        f"/audit?since={quote(since, safe='')}", headers=acct["headers"]
    )
    assert [r["action"] for r in recent.json()] == ["api_key.created"]


async def test_get_audit_never_returns_other_tenant_or_null_tenant_rows(
    client, db, tenant_factory
):
    a = await tenant_factory()
    b = await tenant_factory()
    await record_audit_event(
        db, action="auth.login.success", tenant_id=a["tenant"].id, commit=True
    )
    await record_audit_event(
        db, action="auth.login.success", tenant_id=b["tenant"].id, commit=True
    )
    await record_audit_event(
        db,
        action="auth.login.failed",
        tenant_id=None,
        actor_email="nobody@example.com",
        commit=True,
    )

    resp = await client.get("/audit", headers=a["headers"])
    assert len(resp.json()) == 1
    assert resp.json()[0]["tenant_id"] == str(a["tenant"].id)


async def test_login_success_writes_audit_event(client, tenant_factory):
    acct = await tenant_factory(password="pw-123456")
    await client.post(
        "/auth/login",
        data={"username": acct["email"], "password": "pw-123456"},
    )

    rows = (await client.get("/audit", headers=acct["headers"])).json()
    assert [r["action"] for r in rows] == ["auth.login.success"]
    assert rows[0]["actor_email"] == acct["email"]
    assert rows[0]["actor_user_id"] == str(acct["user"].id)


async def test_login_wrong_password_writes_audit_event_with_known_tenant(
    client, tenant_factory
):
    acct = await tenant_factory(password="pw-123456")
    resp = await client.post(
        "/auth/login",
        data={"username": acct["email"], "password": "wrong"},
    )
    assert resp.status_code == 401

    rows = (await client.get("/audit", headers=acct["headers"])).json()
    assert [r["action"] for r in rows] == ["auth.login.failed"]
    assert rows[0]["actor_email"] == acct["email"]


async def test_login_unknown_email_writes_null_tenant_audit_event(
    client, db, tenant_factory
):
    from sqlalchemy import select

    unique_email = f"nobody-{uuid4().hex}@example.com"
    resp = await client.post(
        "/auth/login",
        data={"username": unique_email, "password": "whatever"},
    )
    assert resp.status_code == 401

    row = (
        await db.execute(select(AuditLog).where(AuditLog.actor_email == unique_email))
    ).scalar_one()
    assert row.action == "auth.login.failed"
    assert row.tenant_id is None
    # Confirmed via direct DB access, per spec: never visible through the API.
    acct = await tenant_factory()
    api_rows = (await client.get("/audit", headers=acct["headers"])).json()
    assert api_rows == []


async def test_api_key_create_and_revoke_write_audit_events(client, tenant_factory):
    acct = await tenant_factory()
    h = acct["headers"]

    created = await client.post("/api-keys", json={"name": "ci"}, headers=h)
    key_id = created.json()["id"]

    revoked = await client.delete(f"/api-keys/{key_id}", headers=h)
    assert revoked.status_code == 204

    rows = (await client.get("/audit", headers=h)).json()
    by_action = {r["action"]: r for r in rows}
    assert set(by_action) == {"api_key.created", "api_key.revoked"}
    assert by_action["api_key.created"]["ref_type"] == "api_key"
    assert by_action["api_key.created"]["ref_id"] == key_id
    assert by_action["api_key.revoked"]["ref_id"] == key_id


async def test_api_key_create_rolls_back_when_audit_write_fails(
    client, tenant_factory, monkeypatch
):
    """Proves the same-transaction guarantee from the spec: a broken audit
    write must prevent the API key from being created, not just log a
    warning. The exception propagates through the test client (httpx's
    ASGITransport re-raises unhandled exceptions by default) rather than
    surfacing as an HTTP 500 — that's a property of this test harness, not
    something the app needs to handle specially. The rollback itself is
    guaranteed by app.database.get_db()'s session context manager, which
    rolls back any uncommitted transaction when an exception propagates
    through it."""
    from app.routers import api_keys

    async def _boom(*args, **kwargs):
        raise RuntimeError("simulated audit failure")

    monkeypatch.setattr(api_keys, "record_audit_event", _boom)

    acct = await tenant_factory()
    h = acct["headers"]
    with pytest.raises(RuntimeError, match="simulated audit failure"):
        await client.post("/api-keys", json={"name": "should-not-exist"}, headers=h)

    listing = await client.get("/api-keys", headers=h)
    assert listing.json() == []


def _stub_github_token_validation(monkeypatch):
    from app.routers import content

    async def fake_validate_token(token):
        return {"login": "octocat"}

    monkeypatch.setattr(content, "validate_token", fake_validate_token)


async def test_github_credential_connect_and_disconnect_write_audit_events(
    client, tenant_factory, monkeypatch
):
    _stub_github_token_validation(monkeypatch)
    acct = await tenant_factory()
    h = acct["headers"]

    await client.post(
        "/content/publish/github/credentials",
        json={"token": "github_pat_secret_1234", "display_name": "Main PAT"},
        headers=h,
    )
    await client.delete("/content/publish/github/credentials", headers=h)

    rows = (await client.get("/audit", headers=h)).json()
    by_action = {r["action"]: r for r in rows}
    assert set(by_action) == {
        "github.credentials.connected",
        "github.credentials.disconnected",
    }
    connected = by_action["github.credentials.connected"]
    assert connected["details"] == {"display_name": "Main PAT"}
    # never the token itself, anywhere in the row
    assert "github_pat_secret_1234" not in str(connected)


async def _approved_content(client, headers):
    cid = (
        await client.post("/content", json={"title": "Post"}, headers=headers)
    ).json()["id"]
    await client.post(
        f"/content/{cid}/transition", json={"status": "IN_REVIEW"}, headers=headers
    )
    await client.post(
        f"/content/{cid}/transition", json={"status": "APPROVED"}, headers=headers
    )
    return cid


async def test_generic_publish_writes_audit_event(client, tenant_factory, monkeypatch):
    from app.core.publishers import wordpress

    async def fake_publish(*, title, body, config):
        return {"url": "https://blog.example.com/p/1", "external_ref": "post 1"}

    monkeypatch.setattr(wordpress, "publish", fake_publish)

    acct = await tenant_factory()
    h = acct["headers"]
    cid = await _approved_content(client, h)

    resp = await client.post(
        f"/content/{cid}/publish",
        json={
            "channel": "wordpress",
            "config": {"site_url": "https://blog.example.com"},
        },
        headers=h,
    )
    assert resp.status_code == 201

    rows = (await client.get("/audit?action=content.published", headers=h)).json()
    assert len(rows) == 1
    assert rows[0]["ref_type"] == "content_piece"
    assert rows[0]["ref_id"] == cid
    # PublishRequest.channel is uppercased by a pre-existing validator
    # (app/schemas/publication.py) before it reaches the handler.
    assert rows[0]["details"] == {"channel": "WORDPRESS"}


async def test_github_publish_writes_audit_event(client, tenant_factory, monkeypatch):
    from app.routers import content

    _stub_github_token_validation(monkeypatch)

    async def fake_publish_markdown(**kwargs):
        return {
            "pr_url": "https://github.com/acme/site/pull/1",
            "pr_number": 1,
            "branch": kwargs["branch"],
            "base_branch": kwargs["base_branch"] or "main",
            "path": kwargs["path"],
            "commit_sha": "abc",
        }

    monkeypatch.setattr(content, "publish_markdown", fake_publish_markdown)
    acct = await tenant_factory()
    h = acct["headers"]
    await client.post(
        "/content/publish/github/credentials",
        json={"token": "tenant-token"},
        headers=h,
    )
    cid = await _approved_content(client, h)

    resp = await client.post(
        f"/content/{cid}/publish/github", json={"repo": "acme/site"}, headers=h
    )
    assert resp.status_code == 201

    rows = (await client.get("/audit?action=content.published", headers=h)).json()
    assert len(rows) == 1
    assert rows[0]["ref_id"] == cid
    assert rows[0]["details"] == {"channel": "GITHUB_PR"}


async def test_login_with_oversized_user_agent_does_not_500(client, tenant_factory):
    acct = await tenant_factory(password="pw-123456")
    long_ua = "A" * 500

    ok = await client.post(
        "/auth/login",
        data={"username": acct["email"], "password": "pw-123456"},
        headers={"User-Agent": long_ua},
    )
    assert ok.status_code == 200

    bad = await client.post(
        "/auth/login",
        data={"username": acct["email"], "password": "wrong"},
        headers={"User-Agent": long_ua},
    )
    assert bad.status_code == 401

    rows = (await client.get("/audit", headers=acct["headers"])).json()
    assert any(r["action"] == "auth.login.success" for r in rows)
    assert any(r["action"] == "auth.login.failed" for r in rows)
    assert all(len(r["user_agent"] or "") <= 255 for r in rows)
