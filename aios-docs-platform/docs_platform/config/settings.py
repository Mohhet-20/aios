"""Centralized configuration for the Enterprise Documentation,
Knowledge Portal & Learning Platform."""
from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", protected_namespaces=())

    app_env: str = "development"
    log_level: str = "INFO"
    log_json: bool = False

    database_url: str = "sqlite+aiosqlite:///./docs_platform.db"
    database_echo: bool = False
    database_pool_size: int = 10

    secret_key: str = "dev-secret-key-change-me-in-production-32chars"

    # Documentation core (15 doc types spanning every subsystem of the AIOS)
    doc_types: list[str] = [
        "architecture", "backend", "frontend", "api", "sdk", "workflow", "agent", "prompt",
        "knowledge", "infrastructure", "deployment", "security", "developer", "admin", "enterprise_customer",
    ]
    doc_page_default_visibility: str = "internal"

    # API & SDK documentation / automation
    api_protocol_types: list[str] = ["rest", "graphql", "websocket", "streaming"]
    sdk_languages: list[str] = [
        "python", "typescript", "java", "go", "csharp", "cli",
        "plugin_sdk", "extension_sdk", "webhook_sdk", "mcp_sdk",
    ]
    generation_job_types: list[str] = [
        "api_docs", "schema_docs", "config_docs", "sdk_docs", "changelog",
        "dependency_report", "architecture_report", "code_reference",
    ]

    # Architecture portal
    diagram_types: list[str] = [
        "system_overview", "sequence", "component", "deployment", "infrastructure_map", "service_map", "dependency_graph",
    ]

    # Knowledge base
    kb_article_types: list[str] = [
        "how_to", "best_practice", "troubleshooting", "faq", "release_note",
        "migration_guide", "design_pattern", "reference", "glossary",
    ]

    # Learning platform
    tutorial_types: list[str] = ["getting_started", "interactive_tutorial", "hands_on_lab", "step_by_step_guide"]
    learning_roles: list[str] = ["administrator", "developer", "enterprise_customer"]
    tutorial_pass_threshold_pct: float = 80.0

    # AI documentation assistant
    assistant_confidence_threshold: float = 0.6
    doc_staleness_days: int = 180

    # Search platform
    search_result_limit_default: int = 20
    search_min_query_length: int = 2

    # Versioning
    version_deprecation_notice_days: int = 90

    # Collaboration
    review_approval_min_reviewers: int = 1

    # Analytics
    analytics_freshness_window_days: int = 90

    # Security & governance
    contributor_roles: list[str] = ["viewer", "contributor", "editor", "owner", "admin"]
    visibility_levels: list[str] = ["internal", "public"]

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
