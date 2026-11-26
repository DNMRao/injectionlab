"""Day-3 check: start the docs MCP server as a separate program and use it.

No AI here: we play the agent by hand, to see exactly what an agent will see.
Needs Qdrant running and the index built (scripts/build_docs_index.py).
Run:  uv run python scripts/try_docs_mcp.py
"""

import asyncio
import os
import sys

from mcp import Client, StdioServerParameters


async def main() -> None:
    server = StdioServerParameters(
        command=sys.executable,  # the project's Python
        args=["-m", "injectionlab.mcp_servers.docs_server"],
        env={**os.environ},  # DOCS_COLLECTION / QDRANT_URL could be set here
    )

    async with Client(server) as client:
        # 1) "Which tools do you have?"
        tools = (await client.list_tools()).tools
        print(f"1) Server offers {len(tools)} tools:")
        for t in tools:
            kind = "read" if t.annotations and t.annotations.read_only_hint else "ACT "
            print(f"   [{kind}] {t.name:12s} {t.description.splitlines()[0]}")

        # 2) Search by meaning
        result = await client.call_tool(
            "search_docs", {"query": "A supplier changed their bank account. Can I pay?", "k": 2}
        )
        print("\n2) search_docs returned:\n", result.content[0].text)

        # 3) Read a whole document
        result = await client.call_tool("read_doc", {"name": "travel_policy.md"})
        print("\n3) read_doc(travel_policy.md) returned:\n", result.content[0].text[:250], "...")


if __name__ == "__main__":
    asyncio.run(main())
