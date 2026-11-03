"""Centralized configuration for the Enterprise Tool Execution & Integration Platform."""
from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"
    log_level: str = "INFO"
    log_json: bool = False

    database_url: str = "sqlite+aiosqlite:///./tool_platform.db"
    database_echo: bool = False
    database_pool_size: int = 10

    secret_key: str = "dev-secret-key-change-me-in-production-32chars"

    # Execution defaults — per-tool-version rows can override any of these.
    default_tool_timeout_seconds: int = 60
    default_max_retries: int = 2
    default_retry_backoff_seconds: float = 1.5
    max_concurrent_tool_executions: int = 50
    max_batch_size: int = 100

    # Sandbox defaults
    sandbox_default_memory_limit_mb: int = 512
    sandbox_default_cpu_seconds: int = 30
    sandbox_default_disk_limit_mb: int = 256
    sandbox_default_timeout_seconds: int = 30
    sandbox_network_default_deny: bool = True

    # Credentials
    credential_default_rotation_days: int = 90

    # Scheduler
    scheduler_poll_interval_seconds: int = 5

    # Governance
    workspace_max_concurrent_executions: int = 100
    rate_limit_calls_per_minute: int = 120

    # Plugin marketplace
    require_plugin_signature: bool = True

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
