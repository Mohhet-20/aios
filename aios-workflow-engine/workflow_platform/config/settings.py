"""Centralized configuration for the Enterprise Workflow Orchestration Engine."""
from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"
    log_level: str = "INFO"
    log_json: bool = False

    database_url: str = "sqlite+aiosqlite:///./workflow_platform.db"
    database_echo: bool = False
    database_pool_size: int = 10

    secret_key: str = "dev-secret-key-change-me-in-production-32chars"

    # Execution defaults — per-node-definition rows can override any of these.
    default_node_timeout_seconds: int = 300
    default_max_retries: int = 3
    default_retry_backoff_seconds: float = 2.0
    max_workflow_recursion_depth: int = 10
    max_parallel_branches: int = 20

    # Scheduler
    scheduler_poll_interval_seconds: int = 5

    # Approvals
    default_approval_escalation_hours: int = 24

    # Governance
    workspace_max_concurrent_executions: int = 50

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
