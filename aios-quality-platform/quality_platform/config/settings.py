"""Centralized configuration for the Enterprise Testing, Quality
Engineering & Reliability Platform."""
from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", protected_namespaces=())

    app_env: str = "development"
    log_level: str = "INFO"
    log_json: bool = False

    database_url: str = "sqlite+aiosqlite:///./quality_platform.db"
    database_echo: bool = False
    database_pool_size: int = 10

    secret_key: str = "dev-secret-key-change-me-in-production-32chars"

    # Test Management & Automation (test pyramid)
    test_pyramid_types: list[str] = [
        "unit", "component", "integration", "contract", "api", "database", "ui",
        "workflow", "agent", "prompt", "memory", "tool", "system", "e2e", "acceptance",
    ]
    test_run_flaky_threshold: int = 3
    test_run_history_window: int = 20

    # AI Quality / Evaluation Regression Engine
    ai_quality_dimensions: list[str] = [
        "prompt_accuracy", "reasoning_quality", "planning_quality", "memory_retrieval",
        "tool_selection", "workflow_execution", "agent_collaboration", "groundedness",
        "hallucination_rate", "citation_quality", "instruction_following", "consistency",
        "structured_output",
    ]
    ai_quality_regression_threshold_pct: float = 5.0

    # Performance Testing Engine
    performance_test_types: list[str] = ["load", "stress", "spike", "soak", "scalability", "concurrency"]
    performance_default_duration_seconds: int = 60

    # Chaos Engineering Platform
    chaos_failure_types: list[str] = [
        "node_failure", "database_failure", "network_latency", "packet_loss", "service_shutdown",
        "worker_failure", "queue_failure", "cache_failure", "storage_failure", "gpu_failure",
        "external_api_failure", "region_failure",
    ]
    chaos_max_blast_radius_pct: float = 25.0

    # Security Testing Engine
    security_test_types: list[str] = [
        "authentication", "authorization", "rbac", "prompt_injection", "jailbreak", "secrets",
        "api_security", "dependency_scan", "container_security", "infrastructure_security", "compliance",
    ]
    security_critical_finding_blocks_gate: bool = True

    # API & Workflow Validation
    api_validation_types: list[str] = [
        "schema", "request", "response", "contract", "backward_compatibility",
        "version_compatibility", "sdk_compatibility",
    ]
    workflow_validation_checks: list[str] = [
        "logic", "node_execution", "parallel_execution", "retries", "compensation",
        "timeout_handling", "failure_recovery", "approval_chains", "human_in_the_loop",
    ]

    # Reliability Engineering
    reliability_default_slo_target: float = 99.9
    reliability_error_budget_window_days: int = 30

    # Quality Gates & Coverage Platform
    quality_gate_check_types: list[str] = [
        "test_coverage", "security", "regression", "performance", "reliability",
        "api_compatibility", "documentation", "quality_score",
    ]
    quality_gate_min_score: float = 80.0
    coverage_types: list[str] = ["code", "api", "workflow", "prompt", "agent", "model", "dataset", "ui", "integration"]
    coverage_min_target_pct: float = 80.0

    # Failure Analysis & Risk Analysis
    failure_pattern_min_occurrences: int = 3
    risk_high_threshold: float = 70.0
    risk_critical_threshold: float = 90.0

    # Release Certification Engine
    certification_score_weights: dict[str, float] = {
        "quality": 0.25, "reliability": 0.2, "security": 0.2, "performance": 0.2, "ai_quality": 0.15,
    }
    certification_min_score_for_approval: float = 80.0

    # Observability
    observability_trend_window_days: int = 90

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
