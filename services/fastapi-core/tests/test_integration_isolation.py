"""Integration tests for tenant isolation — the core multi-tenant invariant."""


async def test_tenant_cannot_read_another_tenants_content(client, tenant_factory):
    a = await tenant_factory()
    b = await tenant_factory()

    created = await client.post(
        "/content",
        json={"title": "A's secret", "body": "private"},
        headers=a["headers"],
    )
    a_content_id = created.json()["id"]

    # B cannot GET A's content piece.
    got = await client.get(f"/content/{a_content_id}", headers=b["headers"])
    assert got.status_code == 404

    # B's list does not include A's content.
    b_list = await client.get("/content", headers=b["headers"])
    assert a_content_id not in [c["id"] for c in b_list.json()]


async def test_tenant_cannot_mutate_another_tenants_content(client, tenant_factory):
    a = await tenant_factory()
    b = await tenant_factory()
    a_content_id = (
        await client.post(
            "/content", json={"title": "A owns this"}, headers=a["headers"]
        )
    ).json()["id"]

    # B cannot patch or transition A's content.
    patched = await client.patch(
        f"/content/{a_content_id}", json={"title": "hijacked"}, headers=b["headers"]
    )
    assert patched.status_code == 404

    transitioned = await client.post(
        f"/content/{a_content_id}/transition",
        json={"status": "IN_REVIEW"},
        headers=b["headers"],
    )
    assert transitioned.status_code == 404
