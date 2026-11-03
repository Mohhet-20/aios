"""Centralized configuration for the Multi-Agent AI Platform."""
from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"
    log_level: str = "INFO"
    log_json: bool = False

    database_url: str = "sqlite+aiosqlite:///./agent_platform.db"
    database_echo: bool = False
    database_pool_size: int = 10

    secret_key: str = "dev-secret-key-change-me-in-production-32chars"

    # Governance defaults
    default_approval_required: bool = True

    # Orchestration safety limits — enterprise autonomous execution needs
    # hard ceilings independent of any single agent's own logic, so a
    # buggy or adversarial plan can't recurse or fan out unboundedly.
    max_agent_recursion_depth: int = 6
    max_concurrent_agent_tasks: int = 20
    default_agent_timeout_seconds: float = 120.0
    min_confidence_for_auto_approval: float = 0.75
    rate_limit_tasks_per_minute: int = 60

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()


def reset_settings_cache() -> None:
    get_settings.cache_clear()
