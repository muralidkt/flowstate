"""Runtime configuration — the only module that reads the environment (STANDARDS.md §3)."""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="FLOWSTATE_", env_file=".env", extra="ignore", populate_by_name=True
    )

    environment: Literal["local", "production"] = "local"
    log_level: str = "INFO"

    agent_model: str = "sonnet"
    agent_max_turns: int = 25
    workspace_dir: Path = Path("./.data")
    persona_path: Path = Path(".claude/CLAUDE.md")
    # Unprefixed on purpose — the SDK's conventional variable name.
    anthropic_api_key: str | None = Field(default=None, validation_alias="ANTHROPIC_API_KEY")


@lru_cache
def get_settings() -> Settings:
    return Settings()
