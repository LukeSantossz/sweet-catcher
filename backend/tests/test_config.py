import pytest

from app.config import Settings


def test_settings_defaults_to_development() -> None:
    settings = Settings()
    assert settings.app_env == "development"


def test_settings_reads_app_env_from_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    settings = Settings()
    assert settings.app_env == "production"
