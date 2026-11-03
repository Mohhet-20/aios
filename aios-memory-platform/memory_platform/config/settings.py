"""Centralized configuration for the Enterprise Memory & Knowledge Platform."""
from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"
    log_level: str = "INFO"
    log_json: bool = False

    database_url: str = "sqlite+aiosqlite:///./memory_platform.db"
    database_echo: bool = False
    database_pool_size: int = 10

    secret_key: str = "dev-secret-key-change-me-in-production-32chars"

    # Memory lifecycle defaults — per-type policy rows can override any of these.
    default_memory_retention_days: int = 365
    default_importance_decay_rate: float = 0.02
    working_memory_ttl_seconds: int = 1800
    summarization_trigger_token_count: int = 4000

    # Document Intelligence
    document_chunk_max_tokens: int = 400
    document_chunk_overlap_tokens: int = 50

    # Retrieval defaults
    default_top_k: int = 10
    hybrid_search_semantic_weight: float = 0.7
    context_token_budget: int = 8000

    # Governance
    retention_enforcement_enabled: bool = True

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
