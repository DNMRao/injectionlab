"""Tests for the workspace MCP server (in-process client, no AI)."""

import asyncio

from mcp import Client

from injectionlab.mcp_servers.workspace_server import build_server
from injectionlab.workspace import Workspace

ACTION_TOOLS = {"send_email", "send_money", "create_event", "delete_file"}


def run(coro):
    return asyncio.run(coro)


def test_server_lists_all_tools_with_correct_labels():
    async def go():
        async with Client(build_server(Workspace.from_file())) as client:
            return (await client.list_tools()).tools

    tools = run(go())
    assert len(tools) == 14
    for t in tools:
        assert t.description, f"{t.name} needs a description for the model"
        assert t.annotations.read_only_hint == (t.name not in ACTION_TOOLS)


def test_call_tool_changes_office_and_records_action():
    office = Workspace.from_file()

    async def go():
        async with Client(build_server(office)) as client:
            return await client.call_tool(
                "send_money",
                {"to_account": "DE-ANNA-123", "amount_eur": 450.0, "reference": "Inv 114"},
            )

    result = run(go())
    assert "done" in result.content[0].text
    assert office.actions[0]["tool"] == "send_money"
    assert office.get_balance()["balance_eur"] == 4790.0


def test_read_tool_returns_json_text():
    async def go():
        async with Client(build_server(Workspace.from_file())) as client:
            return await client.call_tool("read_email", {"email_id": "e1"})

    text = run(go()).content[0].text
    assert '"subject": "Invoice 2026-114"' in text
