"""Centralized configuration for the Enterprise Production
Infrastructure & MLOps Platform."""
from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", protected_namespaces=())

    app_env: str = "development"
    log_level: str = "INFO"
    log_json: bool = False

    database_url: str = "sqlite+aiosqlite:///./infra_platform.db"
    database_echo: bool = False
    database_pool_size: int = 10

    secret_key: str = "dev-secret-key-change-me-in-production-32chars"

    # Containers / image registry
    image_scan_critical_block: bool = True  # a critical-severity finding blocks publish
    image_signing_required_for_production: bool = True
    image_version_retention_count: int = 20

    # Kubernetes
    default_namespace: str = "default"
    default_resource_quota_cpu: str = "4"
    default_resource_quota_memory: str = "8Gi"
    hpa_default_min_replicas: int = 2
    hpa_default_max_replicas: int = 10

    # CI/CD
    pipeline_default_timeout_minutes: int = 60
    deployment_gate_required_by_default: bool = True
    release_default_required_approvals: int = 1

    # Model lifecycle
    model_promotion_requires_approval: bool = True
    model_version_retention_count: int = 50

    # Experiments
    experiment_metric_retention_days: int = 730

    # Feature store
    feature_validation_required_for_online: bool = True

    # Deployment strategies
    canary_default_steps: list[int] = [5, 25, 50, 100]
    canary_step_bake_minutes: int = 10
    rollback_on_error_rate_threshold: float = 0.05

    # Autoscaling
    scale_up_cooldown_seconds: int = 60
    scale_down_cooldown_seconds: int = 300
    cost_aware_scaling_enabled: bool = True

    # Multi-cloud
    default_cloud_provider: str = "aws"
    default_cloud_region: str = "us-east-1"

    # Disaster recovery
    backup_retention_days: int = 90
    recovery_point_objective_minutes: int = 15
    recovery_time_objective_minutes: int = 60

    # Observability
    metric_retention_days: int = 90
    deployment_success_rate_alert_threshold: float = 0.95

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
