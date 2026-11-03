"""Centralized configuration for the Enterprise Collaboration &
Workspace Platform."""
from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"
    log_level: str = "INFO"
    log_json: bool = False

    database_url: str = "sqlite+aiosqlite:///./collaboration_platform.db"
    database_echo: bool = False
    database_pool_size: int = 10

    secret_key: str = "dev-secret-key-change-me-in-production-32chars"

    # Workspaces / quotas
    default_workspace_project_quota: int = 200
    default_workspace_member_quota: int = 500
    workspace_template_default: str = "blank"

    # Real-time collaboration
    presence_heartbeat_ttl_seconds: int = 30
    presence_stale_sweep_interval_seconds: int = 60
    max_concurrent_editors_per_asset: int = 50
    optimistic_lock_conflict_retry_limit: int = 3

    # Comments
    comment_max_length: int = 10000
    comment_edit_window_minutes: int = 1440  # 24h — after this, edits still allowed but flagged old
    max_mentions_per_comment: int = 25

    # Notifications
    notification_digest_batch_size: int = 50
    notification_digest_interval_hours: int = 24
    email_notifications_enabled_by_default: bool = True

    # Versioning
    version_snapshot_max_bytes: int = 2_000_000
    auto_version_on_every_save: bool = True
    release_tag_pattern: str = r"^v\d+\.\d+\.\d+$"

    # Approvals
    default_required_approvals: int = 1
    approval_request_ttl_days: int = 30

    # Sharing / security
    external_share_link_ttl_days: int = 30
    sharing_link_token_bytes: int = 32
    audit_log_retention_days: int = 730

    # Search
    recent_items_per_user_limit: int = 50
    saved_search_limit_per_user: int = 100

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
