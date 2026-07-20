"""Runtime configuration — the only module that reads the environment (STANDARDS.md §3)."""

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="FLOWSTATE_", env_file=".env", extra="ignore")

    environment: Literal["local", "production"] = "local"
    log_level: str = "INFO"


@lru_cache
def get_settings() -> Settings:
    return Settings()
