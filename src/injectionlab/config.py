"""All settings come from environment variables / .env — never hard-coded."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    llm_base_url: str = "https://api.groq.com/openai/v1"
    llm_api_key: str = ""
    llm_model: str = "openai/gpt-oss-20b"

    qdrant_url: str = "http://localhost:6333"
    mlflow_tracking_uri: str = "http://localhost:5000"
    runs_dir: str = "runs"


@lru_cache
def get_settings() -> Settings:
    return Settings()
