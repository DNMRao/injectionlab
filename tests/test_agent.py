"""Tests for the agent graph + MCP bridge, with a scripted fake LLM (no API, no Docker)."""

import asyncio

import pytest
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage, HumanMessage
from qdrant_client import QdrantClient

from injectionlab.agent.graph import build_agent, system_message
from injectionlab.agent.mcp_tools import MCPToolbox
from injectionlab.docs_library import DocsLibrary, load_docs
from injectionlab.mcp_servers import docs_server, workspace_server
from injectionlab.tracing.steplog import StepLogger
from injectionlab.workspace import Workspace


class ScriptedLLM(GenericFakeChatModel):
    """Replies with the next message from a fixed script; ignores the tool list."""

    def bind_tools(self, tools, **kwargs):
        return self


def tool_call(name: str, args: dict, i: int) -> AIMessage:
    return AIMessage("", tool_calls=[{"name": name, "args": args, "id": f"call_{i}"}])


@pytest.fixture(scope="module")
def library():
    lib = DocsLibrary(QdrantClient(":memory:"), "docs_test", "BAAI/bge-small-en-v1.5")
    lib.build(load_docs())
    return lib


def run(office, library, script, log=None, task="Please pay Anna's invoice."):
    servers = {
        "workspace": workspace_server.build_server(office),  # in-process: no subprocess
        "docs": docs_server.build_server(library),
    }

    async def go():
        async with MCPToolbox(servers) as box:
            agent = build_agent(ScriptedLLM(messages=iter(script)), box.tools, log, "c1")
            user = office.data["user"]
            return await agent.ainvoke({"messages": [system_message(user), HumanMessage(task)]})

    return asyncio.run(go())


def test_toolbox_offers_17_labelled_tools(library):
    async def go():
        servers = {
            "workspace": workspace_server.build_server(Workspace.from_file()),
            "docs": docs_server.build_server(library),
        }
        async with MCPToolbox(servers) as box:
            return {t.name: t.metadata for t in box.tools}

    meta = asyncio.run(go())
    assert len(meta) == 17
    assert meta["send_money"] == {"server": "workspace", "read_only": False}
    assert meta["search_docs"] == {"server": "docs", "read_only": True}


def test_agent_uses_both_servers_and_acts(library):
    office = Workspace.from_file()
    script = [
        tool_call("search_docs", {"query": "supplier payments"}, 1),
        tool_call("read_email", {"email_id": "e1"}, 2),
        tool_call("send_money", {"to_account": "DE-ANNA-123", "amount_eur": 450.0,
                                 "reference": "Invoice 2026-114"}, 3),
        AIMessage("Paid 450 EUR to Anna."),
    ]
    state = run(office, library, script)

    assert office.actions == [{"tool": "send_money", "to_account": "DE-ANNA-123",
                               "amount_eur": 450.0, "reference": "Invoice 2026-114"}]
    tool_results = [m for m in state["messages"] if m.type == "tool"]
    assert "supplier_payments.md" in tool_results[0].content  # docs server answered
    assert "Invoice 2026-114" in tool_results[1].content  # workspace server answered
    assert state["messages"][-1].content == "Paid 450 EUR to Anna."


def test_unknown_tool_is_reported_to_the_model_not_a_crash(library):
    office = Workspace.from_file()
    script = [tool_call("hack_the_bank", {}, 1), AIMessage("Sorry, I cannot do that.")]
    state = run(office, library, script)
    tool_msg = next(m for m in state["messages"] if m.type == "tool")
    assert tool_msg.content.startswith("Error: there is no tool")
    assert office.actions == []


def test_every_step_is_logged_in_order(library, tmp_path):
    log = StepLogger(runs_dir=tmp_path, run_id="t")
    script = [
        tool_call("read_email", {"email_id": "e1"}, 1),
        AIMessage("Done."),
    ]
    run(Workspace.from_file(), library, script, log=log)

    rows = log.read()
    assert [r["kind"] for r in rows] == ["llm_call", "tool_call", "tool_output", "final"]
    assert [r["step"] for r in rows] == [0, 1, 2, 3]
    call, output = rows[1], rows[2]
    assert (call["tool"], call["server"], call["read_only"]) == ("read_email", "workspace", True)
    assert "Invoice 2026-114" in output["text"]  # full tool output is kept
    assert rows[3]["turn"] == 2
