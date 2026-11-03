"""SDK-side exception hierarchy, mapped from HTTP status codes
returned by the AIOS Developer Platform API. Every raised error
carries the original `status_code` and decoded response `body` so a
caller can log or branch on it without re-parsing the response."""
from __future__ import annotations


class AiosSdkError(Exception):
    """Base class for every error this SDK raises."""


class AiosConnectionError(AiosSdkError):
    """Raised when the underlying HTTP transport fails entirely
    (DNS failure, connection refused, timeout exhausted after retries)."""


class AiosApiError(AiosSdkError):
    def __init__(self, message: str, *, status_code: int, body: object = None):
        super().__init__(message)
        self.status_code = status_code
        self.body = body


class AiosAuthError(AiosApiError):
    """401 — the API key is missing, invalid, revoked, or expired."""


class AiosPermissionError(AiosApiError):
    """403 — the API key is valid but lacks the required scope."""


class AiosNotFoundError(AiosApiError):
    """404."""


class AiosConflictError(AiosApiError):
    """409 — e.g. a duplicate package version or plugin name."""


class AiosValidationError(AiosApiError):
    """422 — the request body failed server-side validation."""


class AiosRateLimitError(AiosApiError):
    """429 — the API key exceeded its requests-per-minute budget.
    Carries `retry_after_seconds` when the server supplies a
    `Retry-After` header, so a caller can back off intelligently
    instead of guessing."""

    def __init__(self, message: str, *, status_code: int, body: object = None, retry_after_seconds: float | None = None):
        super().__init__(message, status_code=status_code, body=body)
        self.retry_after_seconds = retry_after_seconds


class AiosServerError(AiosApiError):
    """5xx — the platform itself failed. Safe to retry."""


_STATUS_TO_ERROR = {
    401: AiosAuthError,
    403: AiosPermissionError,
    404: AiosNotFoundError,
    409: AiosConflictError,
    422: AiosValidationError,
    429: AiosRateLimitError,
}


def error_for_status(status_code: int, *, message: str, body: object = None, retry_after_seconds: float | None = None) -> AiosApiError:
    if status_code == 429:
        return AiosRateLimitError(message, status_code=status_code, body=body, retry_after_seconds=retry_after_seconds)
    if status_code >= 500:
        return AiosServerError(message, status_code=status_code, body=body)
    error_cls = _STATUS_TO_ERROR.get(status_code, AiosApiError)
    return error_cls(message, status_code=status_code, body=body)
