"""Integration tests for team invites (create, list, revoke, accept)."""

import uuid

import pytest


@pytest.fixture
def allow_admin(monkeypatch):
    """This repo's local dev environment has no OpenFGA store configured, so
    authz.check()/write_membership() fail closed here regardless of the real
    permission logic being tested."""
    from app.core import authz

    async def _allow(user_id: str, relation: str, object_id: str) -> bool:
        return True

    async def _noop(user_id, tenant_id, role="member"):
        return None

    monkeypatch.setattr(authz.authz_client, "check", _allow)
    monkeypatch.setattr(authz.authz_client, "write_membership", _noop)


@pytest.fixture
def no_smtp(monkeypatch):
    """The dev Mailpit container isn't necessarily running in this test env
    — invite creation is best-effort on the email send, so stub it out to
    isolate the tests from that dependency."""
    from app.routers import invites

    monkeypatch.setattr(invites, "_send_invite_email", lambda *a, **k: None)


async def test_create_invite_requires_auth(client):
    resp = await client.post("/invites", json={"email": "new@example.com"})
    assert resp.status_code == 401


async def test_create_invite_requires_admin(client, tenant_factory, no_smtp):
    acct = await tenant_factory()
    resp = await client.post(
        "/invites", json={"email": "new@example.com"}, headers=acct["headers"]
    )
    assert resp.status_code == 403


async def test_create_invite_happy_path(client, tenant_factory, allow_admin, no_smtp):
    acct = await tenant_factory()
    resp = await client.post(
        "/invites", json={"email": "new@example.com"}, headers=acct["headers"]
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["email"] == "new@example.com"
    assert body["role"] == "member"
    assert body["status"] == "PENDING"


async def test_create_invite_rejects_existing_member(
    client, tenant_factory, allow_admin, no_smtp
):
    acct = await tenant_factory()
    resp = await client.post(
        "/invites", json={"email": acct["email"]}, headers=acct["headers"]
    )
    assert resp.status_code == 409


async def test_create_invite_rejects_duplicate_pending_invite(
    client, tenant_factory, allow_admin, no_smtp
):
    acct = await tenant_factory()
    first = await client.post(
        "/invites", json={"email": "new@example.com"}, headers=acct["headers"]
    )
    assert first.status_code == 201

    second = await client.post(
        "/invites", json={"email": "new@example.com"}, headers=acct["headers"]
    )
    assert second.status_code == 409


async def test_create_invite_rejects_invalid_role(
    client, tenant_factory, allow_admin, no_smtp
):
    acct = await tenant_factory()
    resp = await client.post(
        "/invites",
        json={"email": "new@example.com", "role": "owner"},
        headers=acct["headers"],
    )
    assert resp.status_code == 422


async def test_list_invites_returns_tenant_invites(
    client, tenant_factory, allow_admin, no_smtp
):
    acct = await tenant_factory()
    await client.post(
        "/invites", json={"email": "a@example.com"}, headers=acct["headers"]
    )
    await client.post(
        "/invites", json={"email": "b@example.com"}, headers=acct["headers"]
    )

    resp = await client.get("/invites", headers=acct["headers"])
    assert resp.status_code == 200
    emails = {i["email"] for i in resp.json()}
    assert emails == {"a@example.com", "b@example.com"}


async def test_list_invites_is_tenant_scoped(client, tenant_factory, allow_admin, no_smtp):
    a = await tenant_factory()
    b = await tenant_factory()
    await client.post("/invites", json={"email": "x@example.com"}, headers=a["headers"])

    resp = await client.get("/invites", headers=b["headers"])
    assert resp.status_code == 200
    assert resp.json() == []


async def test_revoke_invite(client, tenant_factory, allow_admin, no_smtp):
    acct = await tenant_factory()
    created = await client.post(
        "/invites", json={"email": "new@example.com"}, headers=acct["headers"]
    )
    invite_id = created.json()["id"]

    resp = await client.delete(f"/invites/{invite_id}", headers=acct["headers"])
    assert resp.status_code == 204

    listed = await client.get("/invites", headers=acct["headers"])
    assert listed.json()[0]["status"] == "REVOKED"


async def test_revoke_already_revoked_invite_409(client, tenant_factory, allow_admin, no_smtp):
    acct = await tenant_factory()
    created = await client.post(
        "/invites", json={"email": "new@example.com"}, headers=acct["headers"]
    )
    invite_id = created.json()["id"]
    await client.delete(f"/invites/{invite_id}", headers=acct["headers"])

    resp = await client.delete(f"/invites/{invite_id}", headers=acct["headers"])
    assert resp.status_code == 409


async def test_list_members_includes_the_inviting_admin(
    client, tenant_factory, allow_admin
):
    acct = await tenant_factory()
    resp = await client.get("/invites/members", headers=acct["headers"])
    assert resp.status_code == 200
    emails = {m["email"] for m in resp.json()}
    assert acct["email"] in emails


async def test_accept_invite_creates_a_second_user_in_the_same_tenant(
    client, tenant_factory, allow_admin, no_smtp, db
):
    from sqlalchemy import select
    from app.models.invite import Invite
    from app.models.user import User

    acct = await tenant_factory()
    created = await client.post(
        "/invites", json={"email": "teammate@example.com"}, headers=acct["headers"]
    )
    assert created.status_code == 201

    invite = await db.scalar(
        select(Invite).where(Invite.email == "teammate@example.com")
    )
    assert invite is not None

    resp = await client.post(
        f"/invites/{invite.token}/accept",
        json={"display_name": "Teammate", "password": "pw-123456"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["access_token"]

    me = await client.get(
        "/auth/me", headers={"Authorization": f"Bearer {body['access_token']}"}
    )
    assert me.status_code == 200
    assert me.json()["tenant_id"] == str(acct["tenant"].id)

    user = await db.scalar(select(User).where(User.email == "teammate@example.com"))
    assert user is not None
    assert user.tenant_id == acct["tenant"].id


async def test_accept_invite_rejects_unknown_token(client):
    resp = await client.post(
        "/invites/not-a-real-token/accept",
        json={"display_name": "Nobody", "password": "pw-123456"},
    )
    assert resp.status_code == 404


async def test_accept_invite_rejects_reuse(client, tenant_factory, allow_admin, no_smtp, db):
    from sqlalchemy import select
    from app.models.invite import Invite

    acct = await tenant_factory()
    await client.post(
        "/invites", json={"email": "onceonly@example.com"}, headers=acct["headers"]
    )
    invite = await db.scalar(
        select(Invite).where(Invite.email == "onceonly@example.com")
    )

    first = await client.post(
        f"/invites/{invite.token}/accept",
        json={"display_name": "First", "password": "pw-123456"},
    )
    assert first.status_code == 200

    second = await client.post(
        f"/invites/{invite.token}/accept",
        json={"display_name": "Second", "password": "pw-654321"},
    )
    assert second.status_code == 409


async def test_accept_invite_rejects_expired(client, tenant_factory, allow_admin, no_smtp, db):
    from datetime import datetime, timedelta, timezone
    from sqlalchemy import select
    from app.models.invite import Invite

    acct = await tenant_factory()
    await client.post(
        "/invites", json={"email": "late@example.com"}, headers=acct["headers"]
    )
    invite = await db.scalar(select(Invite).where(Invite.email == "late@example.com"))
    invite.expires_at = datetime.now(timezone.utc) - timedelta(days=1)
    await db.commit()

    resp = await client.post(
        f"/invites/{invite.token}/accept",
        json={"display_name": "Late", "password": "pw-123456"},
    )
    assert resp.status_code == 410
