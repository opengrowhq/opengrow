"""Integration tests for multi-channel publishing dispatch."""

from types import SimpleNamespace

from sqlalchemy import select

from app.models.github_credential import GitHubCredential


def _stub_token_validation(monkeypatch):
    """Pretend GitHub accepted the PAT — no network in tests."""
    from app.routers import content

    async def fake_validate_token(token):
        return {"login": "octocat"}

    monkeypatch.setattr(content, "validate_token", fake_validate_token)


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


async def test_channels_list(client, tenant_factory):
    acct = await tenant_factory()
    resp = await client.get("/content/publish/channels", headers=acct["headers"])
    assert resp.status_code == 200
    by_name = {c["channel"]: c["implemented"] for c in resp.json()}
    # every advertised channel now has an adapter
    for ch in ("GITHUB_PR", "WORDPRESS", "GHOST", "WEBFLOW", "X", "LINKEDIN", "EMAIL"):
        assert by_name[ch] is True


async def test_publish_wordpress_success(client, tenant_factory, monkeypatch):
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
    body = resp.json()
    assert body["channel"] == "WORDPRESS"
    assert body["status"] == "PUBLISHED"
    assert body["url"] == "https://blog.example.com/p/1"

    # usage metered for the publish
    summary = await client.get("/usage/summary", headers=h)
    kinds = {k["kind"] for k in summary.json()["by_kind"]}
    assert "publish" in kinds


async def test_publish_missing_config_502(client, tenant_factory):
    # Adapter exists but required BYOK config is missing → PublisherError → 502.
    acct = await tenant_factory()
    h = acct["headers"]
    cid = await _approved_content(client, h)
    resp = await client.post(
        f"/content/{cid}/publish", json={"channel": "webflow", "config": {}}, headers=h
    )
    assert resp.status_code == 502


async def test_publish_github_via_generic_is_rejected(client, tenant_factory):
    acct = await tenant_factory()
    h = acct["headers"]
    cid = await _approved_content(client, h)
    resp = await client.post(
        f"/content/{cid}/publish",
        json={"channel": "github_pr", "config": {}},
        headers=h,
    )
    assert resp.status_code == 400


async def test_publish_unknown_channel_400(client, tenant_factory):
    acct = await tenant_factory()
    h = acct["headers"]
    cid = await _approved_content(client, h)
    resp = await client.post(
        f"/content/{cid}/publish", json={"channel": "myspace", "config": {}}, headers=h
    )
    assert resp.status_code == 400


async def test_publish_requires_approval(client, tenant_factory):
    acct = await tenant_factory()
    h = acct["headers"]
    cid = (await client.post("/content", json={"title": "Draft"}, headers=h)).json()[
        "id"
    ]
    resp = await client.post(
        f"/content/{cid}/publish",
        json={"channel": "wordpress", "config": {}},
        headers=h,
    )
    assert resp.status_code == 409  # not approved


async def test_github_config_uses_env_fallback(client, tenant_factory, monkeypatch):
    from app.routers import content

    monkeypatch.setattr(
        content,
        "get_settings",
        lambda: SimpleNamespace(
            GITHUB_TOKEN="env-token", GITHUB_API_URL="https://api.github.com"
        ),
    )
    acct = await tenant_factory()

    resp = await client.get("/content/publish/github/config", headers=acct["headers"])

    assert resp.status_code == 200
    body = resp.json()
    assert body["configured"] is True
    assert body["source"] == "env"
    assert body["has_tenant_credential"] is False
    assert body["token_last4"] is None


async def test_github_credential_upsert_is_redacted_and_wins(
    client, tenant_factory, db, monkeypatch
):
    from app.routers import content

    monkeypatch.setattr(
        content,
        "get_settings",
        lambda: SimpleNamespace(
            GITHUB_TOKEN="env-token", GITHUB_API_URL="https://api.github.com"
        ),
    )
    _stub_token_validation(monkeypatch)
    acct = await tenant_factory()
    h = acct["headers"]

    save = await client.post(
        "/content/publish/github/credentials",
        json={"token": "github_pat_tenant_secret_1234", "display_name": "Main PAT"},
        headers=h,
    )
    assert save.status_code == 201
    saved = save.json()
    assert saved == {
        "configured": True,
        "source": "tenant",
        "token_last4": "1234",
        "display_name": "Main PAT",
        "api_url": "https://api.github.com",
    }
    assert "github_pat_tenant_secret_1234" not in save.text

    rows = (
        (
            await db.execute(
                select(GitHubCredential).where(
                    GitHubCredential.tenant_id == acct["tenant"].id
                )
            )
        )
        .scalars()
        .all()
    )
    assert len(rows) == 1
    assert rows[0].token_encrypted != "github_pat_tenant_secret_1234"
    assert rows[0].token_last4 == "1234"

    config = await client.get("/content/publish/github/config", headers=h)
    body = config.json()
    assert body["configured"] is True
    assert body["source"] == "tenant"
    assert body["has_tenant_credential"] is True
    assert body["token_last4"] == "1234"
    assert "github_pat_tenant_secret_1234" not in config.text


async def test_github_credential_delete_falls_back_to_env(
    client, tenant_factory, monkeypatch
):
    from app.routers import content

    monkeypatch.setattr(
        content,
        "get_settings",
        lambda: SimpleNamespace(
            GITHUB_TOKEN="env-token", GITHUB_API_URL="https://api.github.com"
        ),
    )
    _stub_token_validation(monkeypatch)
    acct = await tenant_factory()
    h = acct["headers"]
    await client.post(
        "/content/publish/github/credentials",
        json={"token": "tenant-token"},
        headers=h,
    )

    delete = await client.delete("/content/publish/github/credentials", headers=h)
    assert delete.status_code == 204

    config = await client.get("/content/publish/github/config", headers=h)
    assert config.json()["source"] == "env"


async def test_github_publish_uses_tenant_credential(
    client, tenant_factory, monkeypatch
):
    from app.routers import content

    monkeypatch.setattr(
        content,
        "get_settings",
        lambda: SimpleNamespace(
            GITHUB_TOKEN="", GITHUB_API_URL="https://api.github.com"
        ),
    )
    captured = {}

    async def fake_publish_markdown(**kwargs):
        captured.update(kwargs)
        return {
            "pr_url": "https://github.com/acme/site/pull/1",
            "pr_number": 1,
            "branch": kwargs["branch"],
            "base_branch": kwargs["base_branch"] or "main",
            "path": kwargs["path"],
            "commit_sha": "abc",
        }

    monkeypatch.setattr(content, "publish_markdown", fake_publish_markdown)
    _stub_token_validation(monkeypatch)
    acct = await tenant_factory()
    h = acct["headers"]
    await client.post(
        "/content/publish/github/credentials",
        json={"token": "tenant-token"},
        headers=h,
    )
    cid = await _approved_content(client, h)

    resp = await client.post(
        f"/content/{cid}/publish/github",
        json={"repo": "acme/site"},
        headers=h,
    )

    assert resp.status_code == 201
    assert captured["token"] == "tenant-token"


async def test_github_credential_rejected_token_not_stored(
    client, tenant_factory, db, monkeypatch
):
    from app.core.github_publisher import GitHubPublishError
    from app.routers import content

    async def fake_validate_token(token):
        raise GitHubPublishError("GitHub rejected the token (401 Unauthorized)")

    monkeypatch.setattr(content, "validate_token", fake_validate_token)
    acct = await tenant_factory()
    h = acct["headers"]

    resp = await client.post(
        "/content/publish/github/credentials",
        json={"token": "bad-token"},
        headers=h,
    )

    assert resp.status_code == 400
    rows = (
        (
            await db.execute(
                select(GitHubCredential).where(
                    GitHubCredential.tenant_id == acct["tenant"].id
                )
            )
        )
        .scalars()
        .all()
    )
    assert rows == []
