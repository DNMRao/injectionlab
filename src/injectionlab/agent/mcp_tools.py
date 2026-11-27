"""Our own MCP -> LangChain bridge.

The official `langchain-mcp-adapters` only supports mcp < 2.0, so we write the
small piece we need: open one MCP client per server, list its tools, and turn
each one into a LangChain tool the LLM can call. The connections stay open while
the agent runs (one server process = one test case = one fresh office).

    async with MCPToolbox(default_servers(actions_path="runs/x/actions.jsonl")) as box:
        box.tools        # 17 LangChain tools (14 workspace + 3 docs)
"""

import os
import sys
from contextlib import AsyncExitStack
from typing import Any, Self

from langchain_core.tools import StructuredTool
from mcp import Client, StdioServerParameters
from mcp.types import CallToolResult, Tool


# ------------------------------------------------------------ how to start our servers
def server_params(module: str, **env: str | os.PathLike | None) -> StdioServerParameters:
    """Start one of our MCP servers as a separate program, with extra env "sticky notes"."""
    extra = {k: str(v) for k, v in env.items() if v is not None}
    return StdioServerParameters(
        command=sys.executable, args=["-m", module], env={**os.environ, **extra}
    )


def default_servers(
    actions_path: str | os.PathLike | None = None,
    workspace_path: str | os.PathLike | None = None,
    docs_collection: str | None = None,
) -> dict[str, StdioServerParameters]:
    """Both servers for one test case. None = use the server's default."""
    return {
        "workspace": server_params(
            "injectionlab.mcp_servers.workspace_server",
            INJECTIONLAB_ACTIONS=actions_path,
            INJECTIONLAB_WORKSPACE=workspace_path,
        ),
        "docs": server_params("injectionlab.mcp_servers.docs_server", DOCS_COLLECTION=docs_collection),
    }


# ------------------------------------------------------------ one MCP tool -> one LangChain tool
def _result_text(result: CallToolResult) -> str:
    """The text the model will read. MCP-level errors (e.g. wrong argument type) get 'Error:'."""
    text = "\n".join(c.text for c in result.content if getattr(c, "text", None) is not None)
    if result.is_error and not text.startswith("Error"):
        text = f"Error: {text}"
    return text


def to_langchain_tool(client: Client, tool: Tool, server: str) -> StructuredTool:
    async def call(**kwargs: Any) -> str:
        return _result_text(await client.call_tool(tool.name, kwargs))

    read_only = bool(tool.annotations and tool.annotations.read_only_hint)
    return StructuredTool(
        name=tool.name,
        description=tool.description or "",
        args_schema=tool.input_schema,  # the JSON schema from the server, used as-is
        coroutine=call,
        metadata={"server": server, "read_only": read_only},  # for guardrails and logs
    )


# ------------------------------------------------------------ all servers together
class MCPToolbox:
    """Open connections to several MCP servers and offer all their tools.

    `servers` maps a name to anything `mcp.Client` accepts: StdioServerParameters
    (real setup: separate programs) or an MCPServer object (tests: in-process).
    """

    def __init__(self, servers: dict[str, Any]):
        self.servers = servers
        self.tools: list[StructuredTool] = []

    async def __aenter__(self) -> Self:
        self._stack = AsyncExitStack()  # closes all connections together at the end
        try:
            for name, target in self.servers.items():
                client = await self._stack.enter_async_context(Client(target))
                for tool in (await client.list_tools()).tools:
                    if tool.name in self.by_name:
                        raise ValueError(f"Tool name '{tool.name}' exists on two servers.")
                    self.tools.append(to_langchain_tool(client, tool, name))
        except BaseException:
            await self._stack.aclose()
            raise
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self._stack.aclose()

    @property
    def by_name(self) -> dict[str, StructuredTool]:
        return {t.name: t for t in self.tools}
