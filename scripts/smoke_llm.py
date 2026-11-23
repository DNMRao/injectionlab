"""Day-1 smoke test: can we reach the LLM, and can it call a tool?

Run:  uv run python scripts/smoke_llm.py
"""

from langchain_core.tools import tool

from injectionlab.config import get_settings
from injectionlab.llm import get_chat_model


@tool
def get_balance(account: str) -> str:
    """Return the balance of a bank account."""
    return f"{account}: 1,234.56 EUR"


def main() -> None:
    s = get_settings()
    print(f"Provider: {s.llm_base_url}  model: {s.llm_model}")
    llm = get_chat_model()

    reply = llm.invoke("Reply with exactly: OK")
    print("1) Plain answer:", reply.content.strip())

    msg = llm.bind_tools([get_balance]).invoke("What is the balance of account DE-001?")
    calls = msg.tool_calls
    assert calls, "Model did not call the tool; tool calling is required for this project."
    print("2) Tool call:", calls[0]["name"], calls[0]["args"])
    print("Smoke test passed.")
    


if __name__ == "__main__":
    main()
