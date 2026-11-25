"""Day-2 check: start the workspace MCP server as a separate program and use it.

No AI here: we play the agent by hand, to see exactly what an agent will see.
Run:  uv run python scripts/try_workspace_mcp.py
"""

import asyncio
import os
import sys
import tempfile
from pathlib import Path

from mcp import Client, StdioServerParameters


async def main() -> None:
    actions_file = Path(tempfile.mkdtemp()) / "actions.jsonl"
    server = StdioServerParameters(
        command=sys.executable,  # the project's Python
        args=["-m", "injectionlab.mcp_servers.workspace_server"],
        env={**os.environ, "INJECTIONLAB_ACTIONS": str(actions_file)},
    )

    async with Client(server) as client:
        # 1) "Which tools do you have?"
        tools = (await client.list_tools()).tools
        print(f"1) Server offers {len(tools)} tools:")
        for t in tools:
            kind = "read" if t.annotations and t.annotations.read_only_hint else "ACT "
            print(f"   [{kind}] {t.name:18s} {t.description.splitlines()[0]}")

        # 2) Call a read tool
        result = await client.call_tool("read_email", {"email_id": "e1"})
        print("\n2) read_email(e1) returned:\n", result.content[0].text[:200], "...")

        # 3) Call an action tool
        result = await client.call_tool(
            "send_money",
            {"to_account": "DE-ANNA-123", "amount_eur": 450.0, "reference": "Invoice 2026-114"},
        )
        print("\n3) send_money returned:", result.content[0].text)

    # 4) The server has stopped; the judge reads the action file
    print("\n4) Recorded actions (read by the judge from the file):")
    print("  ", actions_file.read_text().strip())


if __name__ == "__main__":
    asyncio.run(main())
