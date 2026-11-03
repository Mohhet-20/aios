"""Centralized configuration for the Enterprise Monitoring, Logging &
Observability Platform."""
from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"
    log_level: str = "INFO"
    log_json: bool = False

    database_url: str = "sqlite+aiosqlite:///./observability_platform.db"
    database_echo: bool = False
    database_pool_size: int = 10

    secret_key: str = "dev-secret-key-change-me-in-production-32chars"

    # Logging
    log_retention_days: int = 30
    log_max_message_bytes: int = 32_000
    log_rotation_max_events_per_batch: int = 5000
    log_search_default_limit: int = 200
    sensitive_field_names: list[str] = [
        "password", "secret", "token", "api_key", "authorization", "credit_card", "ssn",
    ]

    # Metrics
    metric_retention_days: int = 90
    metric_ingest_max_batch: int = 1000
    metric_aggregation_bucket_seconds: int = 60
    metric_high_cardinality_label_limit: int = 20

    # Tracing
    trace_retention_days: int = 14
    trace_max_spans_per_trace: int = 5000
    trace_sampling_default_rate: float = 1.0

    # Health
    health_stale_after_seconds: int = 120
    health_check_default_interval_seconds: int = 30

    # Alerts
    alert_evaluation_interval_seconds: int = 60
    alert_dedup_window_seconds: int = 300
    default_escalation_delay_minutes: int = 15
    max_escalation_levels: int = 5

    # Incidents
    incident_auto_close_after_resolved_days: int = 7
    default_incident_severity: str = "sev3"

    # Capacity planning
    capacity_forecast_horizon_days: int = 90
    capacity_forecast_min_history_points: int = 7
    capacity_growth_alert_threshold_pct: float = 80.0

    # Reporting
    report_default_lookback_days: int = 30

    # Governance
    audit_log_retention_days: int = 730
    tenant_header_required: bool = True

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
