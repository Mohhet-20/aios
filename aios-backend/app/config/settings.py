"""
Layered application configuration.

Precedence (highest wins): process environment variables > `.env` file >
defaults declared below. This mirrors the Configuration Layer described in
the architecture blueprint: every other module reads config through
this single `Settings` object (injected via `app.dependencies.get_settings`)
rather than reading `os.environ` directly, so there is exactly one place
that knows how configuration is sourced.
"""

from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # --- Application ---
    app_name: str = "AIOS Backend"
    app_env: Literal["development", "staging", "production", "test"] = "development"
    debug: bool = True
    api_v1_prefix: str = "/api/v1"
    app_version: str = "0.1.0"

    # --- Security ---
    secret_key: str = Field(default="dev-secret-change-me", min_length=8)
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 14

    # --- Database ---
    database_url: str = "sqlite+aiosqlite:///./aios.db"
    database_pool_size: int = 10
    database_echo: bool = False

    # --- CORS ---
    cors_origins: list[str] = ["http://localhost:3000"]

    # --- Rate limiting ---
    rate_limit_requests: int = 100
    rate_limit_window_seconds: int = 60

    # --- Observability ---
    log_level: str = "INFO"
    log_json: bool = True

    @field_validator("database_url")
    @classmethod
    def _validate_database_url(cls, v: str) -> str:
        if not v:
            raise ValueError("database_url must not be empty")
        return v

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")


@lru_cache
def get_settings() -> Settings:
    """Process-wide singleton. `lru_cache` gives us the singleton for free
    and makes overriding trivial in tests via `get_settings.cache_clear()`
    plus a monkeypatched environment."""
    return Settings()
