import pytest
from pydantic_settings import SettingsConfigDict

from flowstate.config import Settings


class IsolatedSettings(Settings):
    """Settings that ignore any developer-local .env file, for deterministic tests."""

    model_config = SettingsConfigDict(env_prefix="FLOWSTATE_", env_file=None)


def test_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("FLOWSTATE_ENVIRONMENT", raising=False)
    monkeypatch.delenv("FLOWSTATE_LOG_LEVEL", raising=False)
    settings = IsolatedSettings()
    assert settings.environment == "local"
    assert settings.log_level == "INFO"


def test_env_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FLOWSTATE_ENVIRONMENT", "production")
    settings = IsolatedSettings()
    assert settings.environment == "production"
