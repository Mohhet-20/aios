"""Centralized configuration for the Enterprise Release Engineering,
Distribution & Deployment Platform."""
from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", protected_namespaces=())

    app_env: str = "development"
    log_level: str = "INFO"
    log_json: bool = False

    database_url: str = "sqlite+aiosqlite:///./release_platform.db"
    database_echo: bool = False
    database_pool_size: int = 10

    secret_key: str = "dev-secret-key-change-me-in-production-32chars"

    # Release & version management
    release_channels: list[str] = ["dev", "alpha", "beta", "rc", "stable", "lts", "hotfix", "patch"]
    release_statuses: list[str] = ["draft", "candidate", "approved", "released", "deprecated", "yanked"]
    version_scheme: str = "semver"

    # Artifact management
    artifact_types: list[str] = [
        "backend_package", "frontend_package", "sdk_package", "cli_package", "docker_image",
        "kubernetes_manifest", "helm_chart", "terraform_module", "workflow_template", "agent_template", "prompt_template",
    ]

    # Deployment orchestration
    deployment_targets: list[str] = [
        "cloud", "on_prem", "hybrid", "edge", "multi_region", "multi_cluster", "multi_tenant", "air_gapped", "offline",
    ]
    deployment_statuses: list[str] = ["queued", "in_progress", "succeeded", "failed", "rolled_back"]

    # Rollout strategies
    rollout_strategies: list[str] = [
        "blue_green", "canary", "rolling", "shadow", "progressive", "percentage",
        "region", "organization", "tenant", "feature",
    ]
    rollout_statuses: list[str] = ["planned", "in_progress", "paused", "completed", "aborted"]
    rollout_default_step_pct: float = 10.0

    # Feature flag platform
    feature_flag_scopes: list[str] = ["global", "organization", "workspace", "user", "experiment"]

    # Update infrastructure
    update_types: list[str] = ["automatic", "manual", "scheduled", "delta", "patch", "offline", "rollback"]
    update_statuses: list[str] = ["pending", "downloading", "applying", "applied", "failed", "rolled_back"]

    # License management
    license_types: list[str] = ["enterprise", "organization", "trial", "feature", "seat_based"]
    license_statuses: list[str] = ["active", "expired", "suspended", "revoked", "trial"]
    default_trial_days: int = 30

    # Environment management
    environment_types: list[str] = [
        "development", "testing", "qa", "staging", "production", "sandbox", "customer_preview", "enterprise_dedicated",
    ]

    # Deployment validation
    health_check_targets: list[str] = [
        "application", "api", "database", "workflow", "ai_services", "agent_services",
        "memory_services", "security_platform", "monitoring_platform", "analytics_platform",
    ]

    # Rollback engine
    rollback_types: list[str] = [
        "automatic", "manual", "partial", "database", "configuration", "feature", "model", "infrastructure",
    ]

    # Security & supply chain
    signing_algorithm: str = "sha256"
    require_sbom: bool = True
    require_signature_for_production: bool = True

    # Observability & release analytics
    analytics_adoption_window_days: int = 30

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
