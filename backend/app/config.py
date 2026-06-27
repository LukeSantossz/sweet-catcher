from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"
    database_url: str = "postgresql+psycopg://app:app@localhost:5432/sweet_catcher"
    redis_url: str = "redis://localhost:6379/0"


def get_settings() -> Settings:
    return Settings()
