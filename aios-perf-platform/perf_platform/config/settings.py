"""Centralized configuration for the Enterprise Performance Optimization,
Cost Intelligence & Scalability Platform."""
from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", protected_namespaces=())

    app_env: str = "development"
    log_level: str = "INFO"
    log_json: bool = False

    database_url: str = "sqlite+aiosqlite:///./perf_platform.db"
    database_echo: bool = False
    database_pool_size: int = 10

    secret_key: str = "dev-secret-key-change-me-in-production-32chars"

    # Cache platform
    cache_layers: list[str] = ["memory", "redis", "disk", "cdn", "prompt", "embedding", "response", "workflow", "model", "feature", "api"]
    cache_default_ttl_seconds: int = 300
    memory_cache_max_entries: int = 5000

    # Model routing / LLM cost intelligence
    model_tiers: list[str] = ["small", "medium", "large", "reasoning", "vision", "code"]
    task_complexity_levels: list[str] = ["trivial", "simple", "moderate", "complex", "expert"]
    user_tiers: list[str] = ["free", "pro", "team", "enterprise"]
    # Per-1K-token USD price (input, output) by tier — illustrative published-rate order of magnitude.
    model_tier_pricing_per_1k: dict[str, dict[str, float]] = {
        "small": {"input": 0.00025, "output": 0.00125},
        "medium": {"input": 0.003, "output": 0.015},
        "large": {"input": 0.015, "output": 0.075},
        "reasoning": {"input": 0.02, "output": 0.1},
        "vision": {"input": 0.003, "output": 0.015},
        "code": {"input": 0.003, "output": 0.015},
    }

    # Cost intelligence engine — illustrative per-unit infra rates
    # (USD), configurable per deployment rather than sourced live from
    # a cloud billing API; see README disclosed scope boundaries.
    gpu_cost_per_hour_usd: float = 2.50
    cpu_cost_per_core_hour_usd: float = 0.05
    memory_cost_per_gb_hour_usd: float = 0.01
    storage_cost_per_gb_month_usd: float = 0.02
    bandwidth_cost_per_gb_usd: float = 0.09

    # Cost intelligence engine
    cost_categories: list[str] = ["token", "gpu", "cpu", "memory", "storage", "bandwidth", "infrastructure"]
    cost_entity_types: list[str] = ["user", "organization", "workflow", "agent", "model"]
    default_monthly_budget_usd: float = 1000.0
    budget_alert_thresholds_pct: list[float] = [50.0, 80.0, 100.0]

    # Auto-optimization engine
    recommendation_categories: list[str] = [
        "prompt", "database", "workflow", "caching", "model_downgrade", "infrastructure", "scaling",
    ]
    low_cache_hit_rate_threshold_pct: float = 40.0
    high_latency_p99_ms_threshold: float = 2000.0

    # Observability & SLOs
    latency_percentiles: list[float] = [50.0, 90.0, 95.0, 99.0]
    slo_p95_latency_ms: float = 500.0
    slo_p99_latency_ms: float = 1500.0

    # GPU / infra efficiency
    gpu_pool_types: list[str] = ["shared", "dedicated", "spot", "reserved"]

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
