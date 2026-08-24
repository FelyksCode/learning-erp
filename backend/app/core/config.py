from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Learning ERP"
    database_url: str = "sqlite:///./erp.db"
    cors_origins: list[str] = ["http://localhost:3000"]

    ai_enabled: bool = False
    ai_api_key: str | None = None
    ai_base_url: str = "https://api.openai.com/v1"
    ai_model: str = "gpt-4o-mini"

    jwt_secret: str = "dev-only-secret-change-me-in-production-0123456789abcdef"
    jwt_expire_minutes: int = 720
    auto_create_tables: bool = True


@lru_cache
def get_settings() -> Settings:
    return Settings()
