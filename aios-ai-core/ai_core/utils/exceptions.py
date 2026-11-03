"""AI Core exception hierarchy. Every failure mode the execution engine and
providers can produce is a subclass of AICoreError so callers can catch
broadly or narrowly as needed."""
from __future__ import annotations


class AICoreError(Exception):
    """Base class for every AI Core exception."""


class ProviderError(AICoreError):
    """A provider call failed. Carries enough context for the execution
    engine to decide whether to retry, fail over, or give up."""

    def __init__(self, message: str, *, provider: str, retryable: bool = True, status_code: int | None = None):
        super().__init__(message)
        self.provider = provider
        self.retryable = retryable
        self.status_code = status_code


class ProviderTimeoutError(ProviderError):
    pass


class ProviderRateLimitError(ProviderError):
    def __init__(self, message: str, *, provider: str, retry_after_seconds: float | None = None):
        super().__init__(message, provider=provider, retryable=True, status_code=429)
        self.retry_after_seconds = retry_after_seconds


class ProviderAuthenticationError(ProviderError):
    def __init__(self, message: str, *, provider: str):
        super().__init__(message, provider=provider, retryable=False, status_code=401)


class ModelNotFoundError(AICoreError):
    pass


class NoAvailableModelError(AICoreError):
    """Raised when the router cannot find any candidate model satisfying
    the request's routing hints/capability requirements."""


class AllProvidersFailedError(AICoreError):
    """Raised by the execution engine when every candidate in the fallback
    chain has been tried and failed."""

    def __init__(self, message: str, *, attempts: list[str]):
        super().__init__(message)
        self.attempts = attempts


class RequestValidationError(AICoreError):
    pass


class ResponseValidationError(AICoreError):
    pass


class PromptValidationError(AICoreError):
    """Raised when a PromptTemplate is rendered with missing variables, or
    renders to text still containing unfilled {{placeholder}} markers."""


class StructuredOutputError(AICoreError):
    """Raised when structured output parsing/validation fails after
    exhausting repair retries."""


class ToolExecutionError(AICoreError):
    def __init__(self, message: str, *, tool_name: str):
        super().__init__(message)
        self.tool_name = tool_name


class ToolPermissionDeniedError(ToolExecutionError):
    pass


class ToolNotFoundError(AICoreError):
    pass


class RateLimitExceededError(AICoreError):
    """Raised by the cost/usage tracker when an org/user/project exceeds a
    configured rate or cost limit."""


class CostLimitExceededError(AICoreError):
    def __init__(self, message: str, *, limit_usd: float, current_usd: float):
        super().__init__(message)
        self.limit_usd = limit_usd
        self.current_usd = current_usd
