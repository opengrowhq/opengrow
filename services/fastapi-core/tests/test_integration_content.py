"""Integration tests for the content lifecycle (create → transition → export)."""


async def _create(client, headers, **body):
    body.setdefault("title", "Launch post")
    return await client.post("/content", json=body, headers=headers)


async def test_create_lists_and_gets_content(client, tenant_factory):
    acct = await tenant_factory()
    h = acct["headers"]

    created = await _create(client, h, title="My first post", body="# Hi")
    assert created.status_code == 201
    cp = created.json()
    assert cp["status"] == "DRAFT"
    assert cp["title"] == "My first post"
    cid = cp["id"]

    got = await client.get(f"/content/{cid}", headers=h)
    assert got.status_code == 200
    assert got.json()["body"] == "# Hi"

    listing = await client.get("/content", headers=h)
    assert listing.status_code == 200
    assert cid in [c["id"] for c in listing.json()]


async def test_patch_updates_fields(client, tenant_factory):
    acct = await tenant_factory()
    h = acct["headers"]
    cid = (await _create(client, h)).json()["id"]

    patched = await client.patch(
        f"/content/{cid}",
        json={"title": "Renamed", "body": "new body", "next_action": "  review  "},
        headers=h,
    )
    assert patched.status_code == 200
    assert patched.json()["title"] == "Renamed"
    assert patched.json()["body"] == "new body"
    assert patched.json()["next_action"] == "review"  # trimmed by validator


async def test_create_and_patch_scheduled_publish(client, tenant_factory):
    acct = await tenant_factory()
    h = acct["headers"]

    created = await _create(
        client,
        h,
        due_at="2026-09-01T00:00:00Z",
        scheduled_publish={"channel": "GITHUB_PR", "config": {"repo": "acme/blog"}},
    )
    assert created.status_code == 201
    cp = created.json()
    assert cp["scheduled_publish"] == {
        "channel": "GITHUB_PR",
        "config": {"repo": "acme/blog"},
    }

    patched = await client.patch(
        f"/content/{cp['id']}",
        json={"scheduled_publish": {"channel": "SLACK", "config": {}}},
        headers=h,
    )
    assert patched.json()["scheduled_publish"]["channel"] == "SLACK"

    cleared = await client.patch(
        f"/content/{cp['id']}",
        json={"clear_scheduled_publish": True},
        headers=h,
    )
    assert cleared.json()["scheduled_publish"] is None


async def test_lifecycle_transitions_and_illegal_jump(client, tenant_factory):
    acct = await tenant_factory()
    h = acct["headers"]
    cid = (await _create(client, h)).json()["id"]

    # DRAFT → APPROVED is illegal (must go via IN_REVIEW).
    illegal = await client.post(
        f"/content/{cid}/transition", json={"status": "APPROVED"}, headers=h
    )
    assert illegal.status_code == 409

    # DRAFT → IN_REVIEW → APPROVED is legal.
    r1 = await client.post(
        f"/content/{cid}/transition", json={"status": "IN_REVIEW"}, headers=h
    )
    assert r1.status_code == 200 and r1.json()["status"] == "IN_REVIEW"
    r2 = await client.post(
        f"/content/{cid}/transition", json={"status": "APPROVED"}, headers=h
    )
    assert r2.status_code == 200 and r2.json()["status"] == "APPROVED"

    # Unknown status → 400.
    bad = await client.post(
        f"/content/{cid}/transition", json={"status": "NOPE"}, headers=h
    )
    assert bad.status_code == 400


async def test_export_markdown_has_frontmatter_and_body(client, tenant_factory):
    acct = await tenant_factory()
    h = acct["headers"]
    cid = (await _create(client, h, title="Exportable", body="Hello world")).json()[
        "id"
    ]

    resp = await client.get(f"/content/{cid}/export.md", headers=h)
    assert resp.status_code == 200
    text = resp.text
    assert "title:" in text and "Exportable" in text
    assert "date:" in text
    # internal fields (status, format, id) stay out of published markdown
    assert "status:" not in text
    assert cid not in text
    assert "Hello world" in text


async def test_github_config_disabled_without_token(client, tenant_factory):
    acct = await tenant_factory()
    resp = await client.get("/content/publish/github/config", headers=acct["headers"])
    assert resp.status_code == 200
    assert resp.json()["configured"] is False


async def test_content_requires_auth(client):
    assert (await client.get("/content")).status_code == 401


async def _promote_generation(client, db, tenant_factory, metadata):
    """Create a COMPLETE generation with the given metadata and promote it."""
    from uuid import UUID

    from app.models.generation import Generation, GenerationStatus

    acct = await tenant_factory()
    h = acct["headers"]

    created = await client.post(
        "/generations",
        json={"brief": "Article about compounding", "metadata": metadata},
        headers=h,
    )
    assert created.status_code == 202
    gen_id = created.json()["id"]

    gen = await db.get(Generation, UUID(gen_id))
    gen.status = GenerationStatus.COMPLETE
    gen.result = "# Draft body"
    await db.commit()

    resp = await client.post(
        "/content/from-generation", json={"generation_id": gen_id}, headers=h
    )
    assert resp.status_code == 201
    return resp.json()


async def test_from_generation_stamps_blog_post_for_article_draft(
    client, db, tenant_factory, no_celery
):
    cp = await _promote_generation(
        client,
        db,
        tenant_factory,
        {"kind": "article_draft", "article": {"topic": "Compounding"}},
    )
    assert cp["format"] == "blog_post"


async def test_from_generation_explicit_format_wins(
    client, db, tenant_factory, no_celery
):
    cp = await _promote_generation(
        client,
        db,
        tenant_factory,
        {"format": "essay", "kind": "article_draft"},
    )
    assert cp["format"] == "essay"


async def test_article_outline_generation_with_valid_brief_accepted(
    client, tenant_factory, no_celery
):
    acct = await tenant_factory()
    resp = await client.post(
        "/generations",
        json={
            "brief": "Outline about compounding",
            "metadata": {
                "kind": "article_outline",
                "article": {"topic": "Compounding", "sections_target": 4},
            },
        },
        headers=acct["headers"],
    )
    assert resp.status_code == 202


async def test_article_brief_blank_topic_rejected(client, tenant_factory, no_celery):
    acct = await tenant_factory()
    resp = await client.post(
        "/generations",
        json={
            "brief": "Outline about compounding",
            "metadata": {"kind": "article_outline", "article": {"topic": "  "}},
        },
        headers=acct["headers"],
    )
    assert resp.status_code == 422
    assert "Invalid article brief" in resp.json()["detail"]


async def test_non_article_metadata_still_accepted(client, tenant_factory, no_celery):
    acct = await tenant_factory()
    resp = await client.post(
        "/generations",
        json={"brief": "write a tweet", "metadata": {"foo": "bar"}},
        headers=acct["headers"],
    )
    assert resp.status_code == 202


async def _create_generation(client, headers, **body):
    body.setdefault("brief", "Article about compounding")
    resp = await client.post("/generations", json=body, headers=headers)
    assert resp.status_code == 202
    return resp.json()


async def test_draft_generation_links_parent_outline(client, tenant_factory, no_celery):
    acct = await tenant_factory()
    h = acct["headers"]
    outline = await _create_generation(
        client,
        h,
        metadata={"kind": "article_outline", "article": {"topic": "Compounding"}},
    )
    draft = await _create_generation(
        client,
        h,
        parent_generation_id=outline["id"],
        metadata={
            "kind": "article_draft",
            "article": {"topic": "Compounding"},
            "outline": [{"heading": "Intro", "points": []}],
        },
    )
    assert draft["parent_generation_id"] == outline["id"]

    got = await client.get(f"/generations/{draft['id']}", headers=h)
    assert got.status_code == 200
    assert got.json()["parent_generation_id"] == outline["id"]

    children = await client.get(f"/generations/{outline['id']}/children", headers=h)
    assert children.status_code == 200
    assert [c["id"] for c in children.json()] == [draft["id"]]


async def test_parent_generation_id_invalid_uuid(client, tenant_factory, no_celery):
    acct = await tenant_factory()
    resp = await client.post(
        "/generations",
        json={"brief": "draft", "parent_generation_id": "not-a-uuid"},
        headers=acct["headers"],
    )
    assert resp.status_code == 400


async def test_parent_generation_unknown_is_not_found(
    client, tenant_factory, no_celery
):
    from uuid import uuid4

    acct = await tenant_factory()
    resp = await client.post(
        "/generations",
        json={"brief": "draft", "parent_generation_id": str(uuid4())},
        headers=acct["headers"],
    )
    # Lite authz short-circuits on the DB check; prod may deny at the authz
    # layer first. Either way the link must be rejected.
    assert resp.status_code in (403, 404)


async def test_legacy_metadata_parent_is_hoisted(client, db, tenant_factory, no_celery):
    from uuid import UUID

    from app.models.generation import Generation

    acct = await tenant_factory()
    h = acct["headers"]
    outline = await _create_generation(client, h, brief="outline")
    # Older clients send the parent inside metadata; it must land in the column
    # and NOT remain stored as a metadata key.
    draft = await _create_generation(
        client,
        h,
        metadata={"kind": "article_draft", "parent_generation_id": outline["id"]},
    )
    assert draft["parent_generation_id"] == outline["id"]

    gen = await db.get(Generation, UUID(draft["id"]))
    assert str(gen.parent_generation_id) == outline["id"]
    assert "parent_generation_id" not in (gen.metadata_json or {})
