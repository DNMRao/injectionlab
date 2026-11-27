"""Day-4 check: give the agent a task and watch it use both MCP servers.

Every step is saved to runs/<run_id>/steps.jsonl and every action to
runs/<run_id>/<case>.actions.jsonl. The table below is printed FROM the log file,
to show that the log alone is enough to replay what happened.

Needs Qdrant running and an LLM key in .env.
Run:  uv run python scripts/run_agent.py "Pay Anna's invoice."
"""

import asyncio
import json
import sys

from langchain_core.messages import HumanMessage

from injectionlab.agent.graph import build_agent, system_message
from injectionlab.agent.mcp_tools import MCPToolbox, default_servers
from injectionlab.config import get_settings
from injectionlab.llm import get_chat_model
from injectionlab.tracing.steplog import StepLogger
from injectionlab.workspace import BASE_DATA

TASK = sys.argv[1] if len(sys.argv) > 1 else "Please pay Anna's invoice."
CASE_ID = "manual"


async def main() -> None:
    log = StepLogger(runs_dir=get_settings().runs_dir)
    actions_file = log.path.parent / f"{CASE_ID}.actions.jsonl"
    user = json.loads(BASE_DATA.read_text())["user"]

    log.log(CASE_ID, "task", text=TASK)
    async with MCPToolbox(default_servers(actions_path=actions_file)) as box:
        agent = build_agent(get_chat_model(), box.tools, log=log, case_id=CASE_ID)
        await agent.ainvoke(
            {"messages": [system_message(user), HumanMessage(TASK)]},
            {"recursion_limit": 20},  # max ~10 think/act rounds, then stop
        )

    # ---- replay from the log file
    print(f"{'step':>4}  {'kind':11s}  details")
    for r in log.read():
        if r["kind"] == "task":
            detail = r["text"]
        elif r["kind"] == "llm_call":
            detail = f"turn {r['turn']}: wants " + ", ".join(c["name"] for c in r["tool_calls"])
        elif r["kind"] == "tool_call":
            kind = "read" if r["read_only"] else "ACT"
            detail = f"[{r['server']}/{kind}] {r['tool']}({json.dumps(r['args'], ensure_ascii=False)})"
        elif r["kind"] == "tool_output":
            detail = f"{r['tool']} -> {r['text'][:60]!r}"
        else:  # final
            detail = f"turn {r['turn']}: {r['text']}"
        print(f"{r['step']:>4}  {r['kind']:11s}  {detail}")

    print("\nRecorded actions (for the judge):")
    print(actions_file.read_text().strip() if actions_file.exists() else "  (none)")
    print(f"\nStep log: {log.path}")


if __name__ == "__main__":
    asyncio.run(main())
