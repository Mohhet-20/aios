"""Centralized configuration for the Enterprise Analytics, Business
Intelligence & Executive Reporting Platform."""
from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", protected_namespaces=())

    app_env: str = "development"
    log_level: str = "INFO"
    log_json: bool = False

    database_url: str = "sqlite+aiosqlite:///./analytics_platform.db"
    database_echo: bool = False
    database_pool_size: int = 10

    secret_key: str = "dev-secret-key-change-me-in-production-32chars"

    # Data warehouse / metrics registry
    warehouse_supported_sources: list[str] = [
        "authentication", "organizations", "users", "agents", "workflows", "prompts",
        "models", "memory", "knowledge", "tools", "api_gateway", "infrastructure",
        "security", "monitoring", "deployments", "developer_platform",
    ]
    warehouse_event_retention_days: int = 400
    warehouse_batch_ingest_max_size: int = 500

    # Analytics / aggregation engine
    analytics_supported_domains: list[str] = ["business", "ai", "financial", "performance"]
    analytics_rollup_periods: list[str] = ["hourly", "daily", "weekly", "monthly"]
    analytics_default_rollup_period: str = "daily"

    # KPI engine
    kpi_supported_scopes: list[str] = [
        "custom", "organization", "workspace", "engineering", "ai", "business", "executive",
    ]
    kpi_trend_window_days: int = 90

    # Reporting platform
    report_supported_types: list[str] = [
        "executive", "engineering", "ai_performance", "security", "financial",
        "compliance", "operational", "usage", "custom",
    ]
    report_default_format: str = "json"

    # Forecasting engine
    forecast_supported_types: list[str] = [
        "usage", "cost", "capacity", "growth", "resource", "performance_trend", "anomaly", "risk",
    ]
    forecast_default_horizon_days: int = 30
    forecast_min_history_points: int = 3

    # Recommendation engine
    recommendation_supported_categories: list[str] = [
        "infrastructure_optimization", "cost_optimization", "prompt_optimization",
        "workflow_optimization", "agent_optimization", "resource_allocation",
        "capacity_planning", "security_improvement",
    ]

    # Visualization / dashboard platform
    visualization_supported_types: list[str] = [
        "line_chart", "bar_chart", "heatmap", "timeline", "trend_chart", "network_graph",
        "tree_map", "geo_map", "scorecard", "table", "custom_widget",
    ]
    dashboard_max_widgets: int = 50

    # Security / governance
    security_row_level_default_mode: str = "tenant_scoped"
    security_audit_retention_days: int = 730

    # Observability
    observability_usage_retention_days: int = 180

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
