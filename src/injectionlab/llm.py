"""One place that creates the chat model, so switching provider is a .env change."""

from langchain_openai import ChatOpenAI

from injectionlab.config import get_settings


def get_chat_model(temperature: float = 0.0) -> ChatOpenAI:
    s = get_settings()
    if not s.llm_api_key:
        raise RuntimeError("LLM_API_KEY is empty — copy .env.example to .env and add your key.")
    return ChatOpenAI(
        base_url=s.llm_base_url,
        api_key=s.llm_api_key,
        model=s.llm_model,
        temperature=temperature,
        max_retries=6,  # retries temporary errors (429, 5xx, timeouts); not a wrong key/model
    )
