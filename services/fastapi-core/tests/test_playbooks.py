"""Playbook versioning: CRUD/activate router behavior, and the resolution
fallback chain used by prompt composition (tenant active -> global active ->
None -> caller's hardcoded default)."""

import uuid


async def test_create_playbook_starts_inactive_and_versioned(client, tenant_factory):
    ctx = await tenant_factory()
    resp = await client.post(
        "/playbooks",
        json={
            "kind": "ARTICLE_OUTLINE",
            "name": "SEO-first outlines",
            "system_template": "You are a senior SEO strategist.",
        },
        headers=ctx["headers"],
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["is_active"] is False
    assert body["version"] == 1
    assert body["kind"] == "ARTICLE_OUTLINE"


async def test_create_rejects_invalid_kind(client, tenant_factory):
    ctx = await tenant_factory()
    resp = await client.post(
        "/playbooks",
        json={"kind": "NOT_A_KIND", "name": "x", "system_template": "y"},
        headers=ctx["headers"],
    )
    assert resp.status_code == 400


async def test_create_rejects_blank_template(client, tenant_factory):
    ctx = await tenant_factory()
    resp = await client.post(
        "/playbooks",
        json={"kind": "ARTICLE_OUTLINE", "name": "x", "system_template": "   "},
        headers=ctx["headers"],
    )
    assert resp.status_code == 422


async def test_second_version_increments_and_activate_swaps_active(
    client, tenant_factory
):
    ctx = await tenant_factory()
    r1 = await client.post(
        "/playbooks",
        json={
            "kind": "ARTICLE_DRAFT",
            "name": "v1",
            "system_template": "v1 template",
        },
        headers=ctx["headers"],
    )
    r2 = await client.post(
        "/playbooks",
        json={
            "kind": "ARTICLE_DRAFT",
            "name": "v2",
            "system_template": "v2 template",
        },
        headers=ctx["headers"],
    )
    assert r1.json()["version"] == 1
    assert r2.json()["version"] == 2

    act1 = await client.post(
        f"/playbooks/{r1.json()['id']}/activate", headers=ctx["headers"]
    )
    assert act1.json()["is_active"] is True

    act2 = await client.post(
        f"/playbooks/{r2.json()['id']}/activate", headers=ctx["headers"]
    )
    assert act2.json()["is_active"] is True

    # only one active at a time
    listing = await client.get(
        "/playbooks", params={"kind": "ARTICLE_DRAFT"}, headers=ctx["headers"]
    )
    active_rows = [p for p in listing.json() if p["is_active"]]
    assert len(active_rows) == 1
    assert active_rows[0]["id"] == r2.json()["id"]


async def test_get_missing_playbook_404s(client, tenant_factory):
    ctx = await tenant_factory()
    resp = await client.get(f"/playbooks/{uuid.uuid4()}", headers=ctx["headers"])
    assert resp.status_code == 404


async def test_playbooks_are_tenant_isolated(client, tenant_factory):
    a = await tenant_factory()
    b = await tenant_factory()
    created = await client.post(
        "/playbooks",
        json={"kind": "GENERIC_COPY", "name": "x", "system_template": "y"},
        headers=a["headers"],
    )
    resp = await client.get(
        f"/playbooks/{created.json()['id']}", headers=b["headers"]
    )
    assert resp.status_code == 404


def test_resolution_falls_back_tenant_then_global_then_none(sync_db):
    from app.core.playbook import get_active_system_template_sync
    from app.models.playbook import Playbook, PlaybookKind
    from app.models.tenant import Tenant

    tenant = Tenant(id=uuid.uuid4(), slug=f"t-{uuid.uuid4().hex[:8]}", name="T")
    sync_db.add(tenant)
    sync_db.commit()

    # No rows at all -> None
    assert (
        get_active_system_template_sync(
            sync_db, tenant.id, PlaybookKind.ARTICLE_OUTLINE
        )
        is None
    )

    # Global default active -> used
    global_pb = Playbook(
        tenant_id=None,
        kind=PlaybookKind.ARTICLE_OUTLINE,
        name="global default",
        version=1,
        system_template="GLOBAL TEMPLATE",
        is_active=True,
    )
    sync_db.add(global_pb)
    sync_db.commit()
    assert (
        get_active_system_template_sync(
            sync_db, tenant.id, PlaybookKind.ARTICLE_OUTLINE
        )
        == "GLOBAL TEMPLATE"
    )

    # Tenant-specific active overrides the global default
    tenant_pb = Playbook(
        tenant_id=tenant.id,
        kind=PlaybookKind.ARTICLE_OUTLINE,
        name="tenant override",
        version=1,
        system_template="TENANT TEMPLATE",
        is_active=True,
    )
    sync_db.add(tenant_pb)
    sync_db.commit()
    assert (
        get_active_system_template_sync(
            sync_db, tenant.id, PlaybookKind.ARTICLE_OUTLINE
        )
        == "TENANT TEMPLATE"
    )

    # Different tenant still only sees the global default
    other_tenant_id = uuid.uuid4()
    assert (
        get_active_system_template_sync(
            sync_db, other_tenant_id, PlaybookKind.ARTICLE_OUTLINE
        )
        == "GLOBAL TEMPLATE"
    )


def test_build_generation_messages_uses_active_playbook(sync_db):
    from app.core.auth import hash_password
    from app.core.generation_messages import build_generation_messages
    from app.models.generation import Generation, GenerationStatus
    from app.models.playbook import Playbook, PlaybookKind
    from app.models.tenant import Tenant
    from app.models.user import User

    tenant = Tenant(id=uuid.uuid4(), slug=f"t-{uuid.uuid4().hex[:8]}", name="T")
    sync_db.add(tenant)
    sync_db.commit()

    user = User(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        email=f"u-{uuid.uuid4().hex[:8]}@example.com",
        password_hash=hash_password("pw-123456"),
        display_name="U",
    )
    sync_db.add(user)
    sync_db.commit()

    active = Playbook(
        tenant_id=tenant.id,
        kind=PlaybookKind.ARTICLE_OUTLINE,
        name="custom",
        version=1,
        system_template="CUSTOM OUTLINE RULES",
        is_active=True,
    )
    sync_db.add(active)
    sync_db.commit()

    gen = Generation(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        owner_id=user.id,
        brief="x",
        status=GenerationStatus.QUEUED,
        metadata_json={
            "kind": "article_outline",
            "article": {"topic": "why founders blog"},
        },
    )
    sync_db.add(gen)
    sync_db.commit()

    messages, _max_tokens = build_generation_messages(sync_db, gen)
    assert messages[0]["role"] == "system"
    assert "CUSTOM OUTLINE RULES" in messages[0]["content"]
