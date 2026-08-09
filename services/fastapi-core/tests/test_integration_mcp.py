"""Integration tests for the MCP JSON-RPC endpoint (agent-facing tools)."""

import json


async def _key_headers(client, tenant_factory):
    acct = await tenant_factory()
    created = await client.post(
        "/api-keys", json={"name": "mcp"}, headers=acct["headers"]
    )
    return {"X-API-Key": created.json()["key"]}, acct


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
