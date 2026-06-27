from pathlib import Path

import pytest

from app.config import Settings


def test_settings_defaults_to_development(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("APP_ENV", raising=False)
    settings = Settings()
    assert settings.app_env == "development"


def test_settings_reads_app_env_from_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    settings = Settings()
    assert settings.app_env == "production"
