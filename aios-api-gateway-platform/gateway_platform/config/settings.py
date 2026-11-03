"""Centralized configuration for the Enterprise API Gateway,
Integration Hub & Service Mesh Platform."""
from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", protected_namespaces=())

    app_env: str = "development"
    log_level: str = "INFO"
    log_json: bool = False

    database_url: str = "sqlite+aiosqlite:///./gateway_platform.db"
    database_echo: bool = False
    database_pool_size: int = 10

    secret_key: str = "dev-secret-key-change-me-in-production-32chars"

    # Gateway core
    gateway_supported_protocols: list[str] = [
        "rest", "graphql", "websocket", "sse", "streaming", "grpc",
    ]
    gateway_supported_visibilities: list[str] = [
        "internal", "external", "public", "private", "partner", "admin",
    ]
    gateway_default_timeout_ms: int = 30000

    # API management
    api_key_prefix: str = "gwk_"
    api_key_default_rate_limit_per_minute: int = 120
    api_default_quota_per_day: int = 100000
    api_current_version: str = "v1"
    api_deprecation_notice_days: int = 90
    jwt_algorithm: str = "HS256"
    jwt_default_ttl_minutes: int = 60

    # Service mesh
    mesh_health_check_interval_seconds: int = 15
    mesh_health_check_failure_threshold: int = 3
    mesh_default_load_balancing_strategy: str = "round_robin"
    mesh_default_retry_attempts: int = 3
    mesh_default_timeout_ms: int = 5000
    mesh_circuit_breaker_failure_threshold: int = 5
    mesh_circuit_breaker_open_seconds: int = 30
    mesh_connection_pool_max_size: int = 50

    # Traffic management
    traffic_canary_max_percent: int = 50
    traffic_mirror_sample_rate: float = 1.0

    # Event platform
    event_max_delivery_attempts: int = 5
    event_retry_backoff_seconds: int = 30
    event_dlq_retention_days: int = 14
    event_replay_window_days: int = 7

    # Integration hub
    integration_supported_connectors: list[str] = [
        "crm", "erp", "email", "calendar", "cloud_storage", "github", "gitlab",
        "jira", "confluence", "slack", "microsoft_teams", "salesforce", "sap",
        "custom_rest", "custom_graphql", "custom_enterprise",
    ]
    integration_sync_default_interval_minutes: int = 15

    # Webhooks
    webhook_max_retry_attempts: int = 5
    webhook_retry_backoff_seconds: int = 30
    webhook_signing_algorithm: str = "sha256"
    webhook_delivery_timeout_seconds: int = 10

    # Protocol translation
    protocol_translation_pairs: list[str] = [
        "rest_graphql", "rest_websocket", "rest_event_stream",
    ]

    # Security
    security_rate_limit_burst_multiplier: float = 1.5
    security_ip_filter_default_mode: str = "allow_all"
    security_geo_restriction_default_mode: str = "allow_all"
    security_request_signing_algorithm: str = "hmac-sha256"

    # Observability / analytics
    observability_metric_retention_days: int = 90
    analytics_retention_days: int = 365

    # Developer experience
    devx_sample_request_max_examples: int = 3
    devx_testing_console_timeout_ms: int = 15000

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
