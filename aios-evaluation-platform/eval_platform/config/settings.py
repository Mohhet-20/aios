"""Centralized configuration for the Enterprise AI Evaluation,
Benchmarking & Observability Platform."""
from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"
    log_level: str = "INFO"
    log_json: bool = False

    database_url: str = "sqlite+aiosqlite:///./eval_platform.db"
    database_echo: bool = False
    database_pool_size: int = 10

    secret_key: str = "dev-secret-key-change-me-in-production-32chars"

    # Evaluation / benchmark execution defaults
    default_evaluation_timeout_seconds: int = 120
    default_max_retries: int = 1
    max_concurrent_evaluation_runs: int = 50
    max_dataset_batch_size: int = 500

    # Hallucination detection
    hallucination_groundedness_threshold: float = 0.5

    # Observability
    observability_event_retention_days: int = 90

    # Governance
    workspace_max_concurrent_runs: int = 100
    rate_limit_calls_per_minute: int = 120
    retention_default_days: int = 365

    # Alerting
    alert_evaluation_poll_interval_seconds: int = 30

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
