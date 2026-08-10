"""Integration tests for the MCP JSON-RPC endpoint (agent-facing tools)."""

import json

import pytest


async def _key_headers(client, tenant_factory):
    acct = await tenant_factory()
    created = await client.post(
        "/api-keys", json={"name": "mcp"}, headers=acct["headers"]
    )
    return {"X-API-Key": created.json()["key"]}, acct


@pytest.fixture
def allow_writer(monkeypatch):
    """Stub authz — this repo's local dev environment has no OpenFGA store
    configured, so authz.check()/bind_resource_to_tenant() always fail
    closed here regardless of the real permission logic being tested."""
    from app.core import authz

    async def _allow(user_id: str, relation: str, object_id: str) -> bool:
        return True

    async def _noop(*args, **kwargs) -> None:
        return None

    monkeypatch.setattr(authz.authz_client, "check", _allow)
    monkeypatch.setattr(authz.authz_client, "bind_resource_to_tenant", _noop)


@pytest.fixture
def no_celery(monkeypatch):
    from app.workers import tasks
    from types import SimpleNamespace

    stub = lambda *a, **k: SimpleNamespace(id="test-task")  # noqa: E731
    monkeypatch.setattr(tasks.run_generation, "delay", stub)
    monkeypatch.setattr(tasks.run_orchestrator, "delay", stub)


async def test_initialize_and_tools_list(client, tenant_factory):
    headers, _ = await _key_headers(client, tenant_factory)

    init = await client.post(
        "/mcp",
        json={"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
        headers=headers,
    )
    assert init.status_code == 200
    body = init.json()
    assert body["result"]["serverInfo"]["name"] == "opengrow"
    assert "protocolVersion" in body["result"]

    tools = await client.post(
        "/mcp",
        json={"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
        headers=headers,
    )
    names = {t["name"] for t in tools.json()["result"]["tools"]}
    assert {
        "list_content",
        "create_content",
        "get_attribution_summary",
        "list_brands",
        "transition_content",
        "list_generations",
        "get_generation",
        "create_generation",
        "list_orchestrator_runs",
        "get_orchestrator_run",
        "create_orchestrator_run",
        "list_publications",
    } <= names


async def test_tools_call_creates_and_lists_content(client, tenant_factory):
    headers, _ = await _key_headers(client, tenant_factory)

    call = await client.post(
        "/mcp",
        json={
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {"name": "create_content", "arguments": {"title": "From agent"}},
        },
        headers=headers,
    )
    assert call.status_code == 200
    result = call.json()["result"]
    assert result["isError"] is False
    created = json.loads(result["content"][0]["text"])
    assert created["title"] == "From agent"
    assert created["status"] == "DRAFT"

    listed = await client.post(
        "/mcp",
        json={
            "jsonrpc": "2.0",
            "id": 4,
            "method": "tools/call",
            "params": {"name": "list_content", "arguments": {}},
        },
        headers=headers,
    )
    items = json.loads(listed.json()["result"]["content"][0]["text"])["items"]
    assert any(i["title"] == "From agent" for i in items)


async def test_tools_call_validation_error_is_soft(client, tenant_factory):
    headers, _ = await _key_headers(client, tenant_factory)
    call = await client.post(
        "/mcp",
        json={
            "jsonrpc": "2.0",
            "id": 5,
            "method": "tools/call",
            "params": {"name": "create_content", "arguments": {}},  # missing title
        },
        headers=headers,
    )
    result = call.json()["result"]
    assert result["isError"] is True


async def test_tools_call_lists_brands(client, tenant_factory):
    headers, _ = await _key_headers(client, tenant_factory)
    listed = await client.post(
        "/mcp",
        json={
            "jsonrpc": "2.0",
            "id": 10,
            "method": "tools/call",
            "params": {"name": "list_brands", "arguments": {}},
        },
        headers=headers,
    )
    assert listed.status_code == 200
    result = listed.json()["result"]
    assert result["isError"] is False
    items = json.loads(result["content"][0]["text"])["items"]
    assert items == []


async def test_tools_call_transitions_content(client, tenant_factory):
    headers, _ = await _key_headers(client, tenant_factory)
    create = await client.post(
        "/mcp",
        json={
            "jsonrpc": "2.0",
            "id": 11,
            "method": "tools/call",
            "params": {"name": "create_content", "arguments": {"title": "To review"}},
        },
        headers=headers,
    )
    content_id = json.loads(create.json()["result"]["content"][0]["text"])["id"]

    call = await client.post(
        "/mcp",
        json={
            "jsonrpc": "2.0",
            "id": 12,
            "method": "tools/call",
            "params": {
                "name": "transition_content",
                "arguments": {"content_id": content_id, "status": "IN_REVIEW"},
            },
        },
        headers=headers,
    )
    result = call.json()["result"]
    assert result["isError"] is False
    updated = json.loads(result["content"][0]["text"])
    assert updated["status"] == "IN_REVIEW"


async def test_tools_call_rejects_illegal_transition(client, tenant_factory):
    headers, _ = await _key_headers(client, tenant_factory)
    create = await client.post(
        "/mcp",
        json={
            "jsonrpc": "2.0",
            "id": 13,
            "method": "tools/call",
            "params": {"name": "create_content", "arguments": {"title": "Draft"}},
        },
        headers=headers,
    )
    content_id = json.loads(create.json()["result"]["content"][0]["text"])["id"]

    call = await client.post(
        "/mcp",
        json={
            "jsonrpc": "2.0",
            "id": 14,
            "method": "tools/call",
            "params": {
                "name": "transition_content",
                "arguments": {"content_id": content_id, "status": "PUBLISHED"},
            },
        },
        headers=headers,
    )
    result = call.json()["result"]
    assert result["isError"] is True


async def test_tools_call_transition_unknown_content_id(client, tenant_factory):
    headers, _ = await _key_headers(client, tenant_factory)
    call = await client.post(
        "/mcp",
        json={
            "jsonrpc": "2.0",
            "id": 15,
            "method": "tools/call",
            "params": {
                "name": "transition_content",
                "arguments": {
                    "content_id": "00000000-0000-0000-0000-000000000000",
                    "status": "IN_REVIEW",
                },
            },
        },
        headers=headers,
    )
    result = call.json()["result"]
    assert result["isError"] is True


async def test_unknown_method_and_unknown_tool(client, tenant_factory):
    headers, _ = await _key_headers(client, tenant_factory)
    bad_method = await client.post(
        "/mcp", json={"jsonrpc": "2.0", "id": 6, "method": "nope"}, headers=headers
    )
    assert bad_method.json()["error"]["code"] == -32601

    bad_tool = await client.post(
        "/mcp",
        json={
            "jsonrpc": "2.0",
            "id": 7,
            "method": "tools/call",
            "params": {"name": "does_not_exist", "arguments": {}},
        },
        headers=headers,
    )
    assert bad_tool.json()["error"]["code"] == -32602


async def test_notification_gets_202(client, tenant_factory):
    headers, _ = await _key_headers(client, tenant_factory)
    note = await client.post(
        "/mcp",
        json={"jsonrpc": "2.0", "method": "notifications/initialized"},
        headers=headers,
    )
    assert note.status_code == 202


async def test_mcp_requires_auth(client):
    resp = await client.post(
        "/mcp", json={"jsonrpc": "2.0", "id": 1, "method": "initialize"}
    )
    assert resp.status_code == 401


# ---- Generations, orchestrator runs, publications ---------------------


async def test_tools_call_creates_and_lists_generations(
    client, tenant_factory, allow_writer, no_celery
):
    headers, _ = await _key_headers(client, tenant_factory)

    created = await client.post(
        "/mcp",
        json={
            "jsonrpc": "2.0",
            "id": 20,
            "method": "tools/call",
            "params": {
                "name": "create_generation",
                "arguments": {"brief": "write a tweet"},
            },
        },
        headers=headers,
    )
    assert created.status_code == 200
    result = created.json()["result"]
    assert result["isError"] is False
    gen = json.loads(result["content"][0]["text"])
    assert gen["status"] == "QUEUED"
    assert gen["brief"] == "write a tweet"

    listed = await client.post(
        "/mcp",
        json={
            "jsonrpc": "2.0",
            "id": 21,
            "method": "tools/call",
            "params": {"name": "list_generations", "arguments": {}},
        },
        headers=headers,
    )
    items = json.loads(listed.json()["result"]["content"][0]["text"])["items"]
    assert any(i["id"] == gen["id"] for i in items)

    fetched = await client.post(
        "/mcp",
        json={
            "jsonrpc": "2.0",
            "id": 22,
            "method": "tools/call",
            "params": {"name": "get_generation", "arguments": {"generation_id": gen["id"]}},
        },
        headers=headers,
    )
    result = fetched.json()["result"]
    assert result["isError"] is False
    fetched_gen = json.loads(result["content"][0]["text"])
    assert fetched_gen["id"] == gen["id"]


async def test_create_generation_requires_brief(client, tenant_factory, allow_writer):
    headers, _ = await _key_headers(client, tenant_factory)
    call = await client.post(
        "/mcp",
        json={
            "jsonrpc": "2.0",
            "id": 23,
            "method": "tools/call",
            "params": {"name": "create_generation", "arguments": {}},
        },
        headers=headers,
    )
    assert call.json()["result"]["isError"] is True


async def test_create_generation_surfaces_403_as_a_soft_tool_error(
    client, tenant_factory
):
    """create_generation reuses the real REST handler, which raises
    HTTPException (not ValueError) for permission failures — this must
    still come back as a JSON-RPC tool error, not a raw HTTP failure."""
    headers, _ = await _key_headers(client, tenant_factory)
    call = await client.post(
        "/mcp",
        json={
            "jsonrpc": "2.0",
            "id": 24,
            "method": "tools/call",
            "params": {"name": "create_generation", "arguments": {"brief": "x"}},
        },
        headers=headers,
    )
    assert call.status_code == 200
    result = call.json()["result"]
    assert result["isError"] is True


async def test_get_generation_unknown_id(client, tenant_factory):
    headers, _ = await _key_headers(client, tenant_factory)
    call = await client.post(
        "/mcp",
        json={
            "jsonrpc": "2.0",
            "id": 25,
            "method": "tools/call",
            "params": {
                "name": "get_generation",
                "arguments": {"generation_id": "00000000-0000-0000-0000-000000000000"},
            },
        },
        headers=headers,
    )
    assert call.json()["result"]["isError"] is True


async def test_tools_call_creates_and_lists_orchestrator_runs(
    client, tenant_factory, allow_writer, no_celery
):
    headers, _ = await _key_headers(client, tenant_factory)

    created = await client.post(
        "/mcp",
        json={
            "jsonrpc": "2.0",
            "id": 26,
            "method": "tools/call",
            "params": {
                "name": "create_orchestrator_run",
                "arguments": {"brief": "write a launch post"},
            },
        },
        headers=headers,
    )
    assert created.status_code == 200
    result = created.json()["result"]
    assert result["isError"] is False
    run = json.loads(result["content"][0]["text"])
    assert run["status"] == "QUEUED"

    listed = await client.post(
        "/mcp",
        json={
            "jsonrpc": "2.0",
            "id": 27,
            "method": "tools/call",
            "params": {"name": "list_orchestrator_runs", "arguments": {}},
        },
        headers=headers,
    )
    items = json.loads(listed.json()["result"]["content"][0]["text"])["items"]
    assert any(i["run_id"] == run["run_id"] for i in items)

    fetched = await client.post(
        "/mcp",
        json={
            "jsonrpc": "2.0",
            "id": 28,
            "method": "tools/call",
            "params": {
                "name": "get_orchestrator_run",
                "arguments": {"run_id": run["run_id"]},
            },
        },
        headers=headers,
    )
    result = fetched.json()["result"]
    assert result["isError"] is False
    fetched_run = json.loads(result["content"][0]["text"])
    assert fetched_run["run_id"] == run["run_id"]


async def test_get_orchestrator_run_unknown_id(client, tenant_factory):
    headers, _ = await _key_headers(client, tenant_factory)
    call = await client.post(
        "/mcp",
        json={
            "jsonrpc": "2.0",
            "id": 29,
            "method": "tools/call",
            "params": {
                "name": "get_orchestrator_run",
                "arguments": {"run_id": "00000000-0000-0000-0000-000000000000"},
            },
        },
        headers=headers,
    )
    result = call.json()["result"]
    assert result["isError"] is True


async def test_tools_call_lists_publications(client, tenant_factory):
    headers, _ = await _key_headers(client, tenant_factory)
    listed = await client.post(
        "/mcp",
        json={
            "jsonrpc": "2.0",
            "id": 30,
            "method": "tools/call",
            "params": {"name": "list_publications", "arguments": {}},
        },
        headers=headers,
    )
    assert listed.status_code == 200
    result = listed.json()["result"]
    assert result["isError"] is False
    items = json.loads(result["content"][0]["text"])["items"]
    assert items == []
