"""Centralized configuration for the Enterprise Developer Platform &
SDK Ecosystem."""
from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", protected_namespaces=())

    app_env: str = "development"
    log_level: str = "INFO"
    log_json: bool = False

    database_url: str = "sqlite+aiosqlite:///./developer_platform.db"
    database_echo: bool = False
    database_pool_size: int = 10

    secret_key: str = "dev-secret-key-change-me-in-production-32chars"

    # API platform
    api_key_prefix: str = "dpk_"
    api_key_default_rate_limit_per_minute: int = 60
    api_rate_limit_burst_multiplier: float = 1.5
    api_current_version: str = "v1"
    api_deprecation_notice_days: int = 90

    # SDK platform
    sdk_supported_languages: list[str] = ["python", "typescript", "java", "go", "csharp"]
    sdk_version_compat_window_majors: int = 2

    # CLI platform
    cli_token_ttl_minutes: int = 43200  # 30 days

    # Plugin SDK
    plugin_signing_required_for_publish: bool = True
    plugin_marketplace_requires_review: bool = True
    plugin_max_dependency_depth: int = 10

    # Extension framework
    extension_point_categories: list[str] = [
        "agent", "prompt", "workflow", "memory", "tool", "model",
        "evaluation", "dashboard", "authentication", "notification", "ui_component",
    ]

    # Webhook platform
    webhook_max_retry_attempts: int = 5
    webhook_retry_backoff_seconds: int = 30
    webhook_signing_algorithm: str = "sha256"
    webhook_delivery_timeout_seconds: int = 10

    # MCP integration
    mcp_session_ttl_minutes: int = 60
    mcp_protocol_version: str = "2024-11-05"

    # Code generation
    codegen_output_formats: list[str] = ["python", "typescript"]

    # Package registry
    package_registry_deprecation_notice_days: int = 180

    # Developer portal / sandbox
    sandbox_ttl_minutes: int = 120
    sandbox_max_concurrent_per_developer: int = 3

    # Developer analytics
    analytics_retention_days: int = 365
    developer_analytics_sample_rate: float = 1.0

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
