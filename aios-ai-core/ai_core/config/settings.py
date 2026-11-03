"""Centralized AI Core configuration. Every provider credential, timeout,
retry policy, routing default, feature flag, and cost/rate limit lives
here — nothing else in the codebase should read an env var directly."""
from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class ProviderSettings(BaseSettings):
    """One block per provider. Kept as plain fields (not a dict) so typos
    in provider names are caught by the type checker, not at runtime."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"

    azure_openai_api_key: str = ""
    azure_openai_endpoint: str = ""
    azure_openai_api_version: str = "2024-06-01"

    anthropic_api_key: str = ""
    anthropic_base_url: str = "https://api.anthropic.com"

    gemini_api_key: str = ""
    gemini_base_url: str = "https://generativelanguage.googleapis.com"

    huggingface_api_key: str = ""
    huggingface_base_url: str = "https://api-inference.huggingface.co"

    ollama_base_url: str = "http://localhost:11434/v1"
    vllm_base_url: str = "http://localhost:8000/v1"
    lmstudio_base_url: str = "http://localhost:1234/v1"
    local_transformers_base_url: str = "http://localhost:9000/v1"


class AICoreSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", protected_namespaces=())

    app_env: str = "development"
    log_level: str = "INFO"
    log_json: bool = False
    debug_include_raw_response: bool = False

    # Execution defaults
    default_request_timeout_seconds: float = Field(default=60.0)
    default_max_retries: int = Field(default=3)
    retry_backoff_multiplier: float = 0.5
    retry_backoff_max_seconds: float = 20.0

    # Routing defaults
    default_routing_strategy: str = "priority"
    canary_traffic_percent: float = Field(default=0.0, ge=0.0, le=100.0)

    # Feature flags
    enable_streaming: bool = True
    enable_tool_calling: bool = True
    enable_structured_output: bool = True
    enable_response_cache: bool = True
    enable_embedding_cache: bool = True

    # Cost / rate limits (defaults; per-org overrides live in UsageTracker)
    daily_cost_limit_usd: float = 100.0
    monthly_cost_limit_usd: float = 2000.0
    rate_limit_requests_per_minute: int = 300

    providers: ProviderSettings = Field(default_factory=ProviderSettings)


@lru_cache
def get_settings() -> AICoreSettings:
    return AICoreSettings()


def reset_settings_cache() -> None:
    """Used by tests that monkeypatch env vars mid-session."""
    get_settings.cache_clear()
