"""Centralized configuration for the Enterprise Authentication,
Organizations & Multi-Tenant Platform."""
from __future__ import annotations

from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEV_SECRET_KEY = "dev-secret-key-change-me-in-production-32chars"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"
    log_level: str = "INFO"
    log_json: bool = False

    database_url: str = "sqlite+aiosqlite:///./identity_platform.db"
    database_echo: bool = False
    database_pool_size: int = 10

    secret_key: str = DEV_SECRET_KEY

    # JWT / sessions
    jwt_algorithm: str = "HS256"
    jwt_access_token_ttl_seconds: int = 900
    jwt_refresh_token_ttl_seconds: int = 2592000  # 30 days
    max_concurrent_sessions_per_user: int = 10
    trusted_device_ttl_days: int = 30

    # Password policy
    password_min_length: int = 12
    password_require_uppercase: bool = True
    password_require_lowercase: bool = True
    password_require_digit: bool = True
    password_require_symbol: bool = True
    password_history_size: int = 5
    password_reset_token_ttl_minutes: int = 60
    email_verification_token_ttl_hours: int = 24
    magic_link_token_ttl_minutes: int = 15

    # Account lockout / brute force
    account_lockout_threshold: int = 5
    account_lockout_window_minutes: int = 15
    account_lockout_duration_minutes: int = 30

    # MFA
    totp_issuer: str = "AIOS"
    totp_period_seconds: int = 30
    totp_digits: int = 6
    recovery_code_count: int = 10

    # Invitations
    invitation_ttl_days: int = 14

    # API keys / service accounts
    api_key_default_ttl_days: int | None = None  # None = no default expiry
    api_key_prefix_length: int = 8

    # Rate limiting / risk
    rate_limit_login_attempts_per_minute: int = 10
    risk_score_high_threshold: float = 0.75

    # Governance / retention
    audit_log_retention_days: int = 730
    login_history_retention_days: int = 365

    # Tenancy quotas
    default_org_seat_quota: int = 25
    default_org_workspace_quota: int = 10

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @model_validator(mode="after")
    def _refuse_weak_signing_key_in_production(self) -> "Settings":
        # Every access token is signed with this key; the development default is public in this repository.
        if self.is_production and (self.secret_key == DEV_SECRET_KEY or len(self.secret_key) < 32):
            raise ValueError("SECRET_KEY must be set to a private value of at least 32 characters in production")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()


def reset_settings_cache() -> None:
    get_settings.cache_clear()
