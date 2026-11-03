"""Centralized configuration for the Enterprise Security, Guardrails &
AI Governance Platform."""
from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"
    log_level: str = "INFO"
    log_json: bool = False

    database_url: str = "sqlite+aiosqlite:///./security_platform.db"
    database_echo: bool = False
    database_pool_size: int = 10

    secret_key: str = "dev-secret-key-change-me-in-production-32chars"
    # Master key used to derive per-secret encryption (Fernet). In
    # production this would come from a real KMS, not an env var — see
    # `encryption/`'s module docstring for the disclosed scope boundary.
    master_encryption_key: str = "dev-master-key-change-me-in-prod-32b!!"

    # Guardrails
    prompt_injection_risk_threshold: float = 0.6
    jailbreak_risk_threshold: float = 0.6
    max_prompt_length: int = 50_000
    guardrail_block_on_high_risk: bool = True

    # PII / DLP
    pii_redaction_placeholder: str = "[REDACTED]"
    dlp_block_on_critical: bool = True

    # Policy engine
    policy_default_scope: str = "organization"
    max_policy_exception_days: int = 90

    # Secrets
    secret_default_ttl_days: int = 365
    secret_rotation_warning_days: int = 30
    secret_version_retention_count: int = 10

    # Risk engine
    risk_score_decay_half_life_days: float = 14.0
    risk_score_high_threshold: float = 75.0
    risk_score_critical_threshold: float = 90.0

    # Threat detection
    brute_force_attempt_threshold: int = 5
    brute_force_window_seconds: int = 300
    api_abuse_rate_threshold: int = 1000
    api_abuse_window_seconds: int = 60

    # Governance
    default_required_approvals: int = 1
    approval_request_ttl_days: int = 30

    # Compliance
    audit_log_retention_days: int = 2555  # ~7 years, common regulatory baseline
    legal_hold_overrides_retention: bool = True
    default_data_residency_region: str = "us"

    # Security events / audit
    security_event_retention_days: int = 730

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
