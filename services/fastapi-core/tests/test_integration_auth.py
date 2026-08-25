"""Integration tests for the auth flow (real app + DB)."""

import uuid

import pytest

from app.config import settings

# _signup_router (app/routers/auth.py) is bound to a separate, unmounted
# APIRouter() at import time when DEPLOYMENT_MODE=lite, so /auth/signup is
# never registered on the running app at all in lite mode — a real 404, not
# a permission/config error a test-time monkeypatch could work around. CI
# (.github/workflows/ci.yml) runs DEPLOYMENT_MODE=lite, so these tests need
# a hosted-mode run to actually exercise; skip rather than fail here.
requires_hosted_mode = pytest.mark.skipif(
    settings.is_lite, reason="/auth/signup only exists when DEPLOYMENT_MODE != lite"
)


async def test_login_returns_token_and_me(client, tenant_factory):
    account = await tenant_factory(password="pw-123456")

    resp = await client.post(
        "/auth/login",
        data={"username": account["email"], "password": "pw-123456"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["access_token"]
    assert body["token_type"] == "bearer"

    me = await client.get(
        "/auth/me", headers={"Authorization": f"Bearer {body['access_token']}"}
    )
    assert me.status_code == 200
    assert me.json()["email"] == account["email"]
    assert me.json()["tenant_slug"] == account["tenant"].slug


async def test_login_wrong_password_401(client, tenant_factory):
    account = await tenant_factory(password="pw-123456")
    resp = await client.post(
        "/auth/login",
        data={"username": account["email"], "password": "wrong"},
    )
    assert resp.status_code == 401


async def test_login_unknown_user_401(client):
    resp = await client.post(
        "/auth/login",
        data={"username": "nobody@example.com", "password": "whatever"},
    )
    assert resp.status_code == 401


async def test_me_requires_auth(client):
    assert (await client.get("/auth/me")).status_code == 401
    bad = await client.get("/auth/me", headers={"Authorization": "Bearer garbage"})
    assert bad.status_code == 401


async def test_register_is_not_in_public_core(client):
    # Signup is a hosted-only concern; the public core must not expose it.
    resp = await client.post(
        "/auth/register",
        json={"email": "x@y.com", "password": "longenough"},
    )
    assert resp.status_code == 404


# ---- Signup (self-service tenant + first-user creation) -------------------


@pytest.fixture
def stub_authz(monkeypatch):
    """This repo's local dev environment has no OpenFGA store configured, so
    the real client's write_membership() fails closed here regardless of the
    real permission-writing logic being tested."""
    from app.core import authz

    async def _noop(user_id, tenant_id, role="member"):
        return None

    monkeypatch.setattr(authz.authz_client, "write_membership", _noop)


def _signup_payload(**overrides):
    suffix = uuid.uuid4().hex[:10]
    payload = {
        "email": f"founder-{suffix}@example.com",
        "password": "pw-123456",
        "display_name": "Founder",
        "tenant_name": f"Acme {suffix}",
    }
    payload.update(overrides)
    return payload


@requires_hosted_mode
async def test_signup_creates_tenant_and_first_user(client, db, stub_authz):
    from sqlalchemy import select
    from app.models.tenant import Tenant
    from app.models.user import User

    payload = _signup_payload()
    resp = await client.post("/auth/signup", json=payload)
    assert resp.status_code == 201
    body = resp.json()
    assert body["access_token"]
    assert body["token_type"] == "bearer"

    me = await client.get(
        "/auth/me", headers={"Authorization": f"Bearer {body['access_token']}"}
    )
    assert me.status_code == 200
    me_body = me.json()
    assert me_body["email"] == payload["email"]
    expected_slug = payload["tenant_name"].lower().replace(" ", "-")
    assert me_body["tenant_slug"] == expected_slug

    tenant = await db.scalar(select(Tenant).where(Tenant.slug == expected_slug))
    assert tenant is not None
    assert tenant.name == payload["tenant_name"]
    assert tenant.billing_plan == "free"  # signup never auto-subscribes

    user = await db.scalar(select(User).where(User.email == payload["email"]))
    assert user is not None
    assert user.tenant_id == tenant.id


@requires_hosted_mode
async def test_signup_rejects_duplicate_email(client, stub_authz):
    payload = _signup_payload()
    first = await client.post("/auth/signup", json=payload)
    assert first.status_code == 201

    second = await client.post(
        "/auth/signup",
        json={**payload, "tenant_name": "Different Co " + uuid.uuid4().hex[:6]},
    )
    assert second.status_code == 409


@requires_hosted_mode
async def test_signup_slugs_collide_safely(client, db, stub_authz):
    """Two different workspaces with the same display name must not collide
    on the tenant slug — the second gets a numeric suffix."""
    from sqlalchemy import select
    from app.models.tenant import Tenant

    tenant_name = f"Acme Collide {uuid.uuid4().hex[:6]}"
    first = await client.post(
        "/auth/signup",
        json=_signup_payload(tenant_name=tenant_name),
    )
    assert first.status_code == 201

    second = await client.post(
        "/auth/signup",
        json=_signup_payload(tenant_name=tenant_name),
    )
    assert second.status_code == 201

    slugs = (
        await db.scalars(select(Tenant.slug).where(Tenant.name == tenant_name))
    ).all()
    base = tenant_name.lower().replace(" ", "-")
    assert sorted(slugs) == [base, f"{base}-2"]


@requires_hosted_mode
async def test_signup_rejects_short_password(client):
    resp = await client.post(
        "/auth/signup", json=_signup_payload(password="short")
    )
    assert resp.status_code == 422


@requires_hosted_mode
async def test_signup_grants_admin_and_writer_access(client, monkeypatch):
    """The first user of a new tenant must be able to do admin-gated things
    (e.g. billing) immediately, not just read/write content — same two
    relations scripts/seed.py grants the demo user."""
    from app.core import authz

    written = []

    async def _capture(user_id, tenant_id, role="member"):
        written.append(role)

    monkeypatch.setattr(authz.authz_client, "write_membership", _capture)

    resp = await client.post("/auth/signup", json=_signup_payload())
    assert resp.status_code == 201
    assert set(written) == {"admin", "member"}
