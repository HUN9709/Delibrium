from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class PanelistSettings(BaseSettings):
    """Process configuration.

    One codebase, many server instances: the same image becomes a GPT, Claude,
    or Gemini server purely through environment variables (PANELIST_SERVER.md
    sections 2 and 14). Model names are never hardcoded in business logic.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    panelist_id: str = "fake-panelist"
    panelist_type: str = "fake"
    provider: str = "fake"
    model_name: str = "fake-1"

    database_url: str = "sqlite+aiosqlite:///./panelist.db"
    max_history_messages: int = 30
    llm_timeout_seconds: int = 60
    default_max_output_tokens: int = 4096

    # Unused in Milestone 1; declared so .env files validate cleanly.
    openai_api_key: str | None = None
    anthropic_api_key: str | None = None
    gemini_api_key: str | None = None


@lru_cache
def get_settings() -> PanelistSettings:
    return PanelistSettings()
