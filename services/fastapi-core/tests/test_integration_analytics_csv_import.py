"""Integration tests for the CSV bulk analytics import endpoint."""

import io


async def test_csv_import_creates_events(client, tenant_factory):
    acct = await tenant_factory()
    h = acct["headers"]

    csv_body = (
        "source_url,channel,visits,signups,revenue_cents\n"
        "https://example.test/a,newsletter,10,2,5000\n"
        "https://example.test/b,,3,0,0\n"
    )
    files = {"file": ("import.csv", io.BytesIO(csv_body.encode()), "text/csv")}
    resp = await client.post(
        "/analytics/import/csv?provider=manual", files=files, headers=h
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["imported_rows"] == 2
    assert (
        body["imported_events"] >= 3
    )  # visits+signups+revenue from row 1, visits from row 2

    summary = await client.get("/analytics/summary", headers=h)
    assert summary.status_code == 200
    assert summary.json()["visits"] == 13
    assert summary.json()["revenue_cents"] == 5000


async def test_csv_import_rejects_non_csv_content_type(client, tenant_factory):
    acct = await tenant_factory()
    files = {"file": ("import.txt", io.BytesIO(b"not a csv"), "application/pdf")}
    resp = await client.post(
        "/analytics/import/csv", files=files, headers=acct["headers"]
    )
    assert resp.status_code == 415


async def test_csv_import_rejects_unknown_columns(client, tenant_factory):
    acct = await tenant_factory()
    csv_body = "visits,made_up_column\n5,oops\n"
    files = {"file": ("import.csv", io.BytesIO(csv_body.encode()), "text/csv")}
    resp = await client.post(
        "/analytics/import/csv", files=files, headers=acct["headers"]
    )
    assert resp.status_code == 400
    assert "made_up_column" in resp.json()["detail"]


async def test_csv_import_rejects_empty_file(client, tenant_factory):
    acct = await tenant_factory()
    files = {"file": ("import.csv", io.BytesIO(b"visits\n"), "text/csv")}
    resp = await client.post(
        "/analytics/import/csv", files=files, headers=acct["headers"]
    )
    assert resp.status_code == 400
    assert "no data rows" in resp.json()["detail"]


async def test_csv_import_requires_auth(client):
    files = {"file": ("import.csv", io.BytesIO(b"visits\n5\n"), "text/csv")}
    resp = await client.post("/analytics/import/csv", files=files)
    assert resp.status_code == 401
