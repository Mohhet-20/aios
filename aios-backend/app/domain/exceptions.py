"""Domain-layer exception re-exports.

The concrete exception hierarchy lives in `app.core.exceptions` so both API
error handling and domain code share one taxonomy (see that module's
docstring for why). This module exists so domain/service code can `from
app.domain.exceptions import NotFoundError` without reaching "up" into
`app.core` by name — a purely cosmetic layering seam, not a second
implementation.
"""

from app.core.exceptions import (
    AIOSError,
    AuthenticationError,
    AuthorizationError,
    ConcurrentModificationError,
    ConflictError,
    ExternalServiceError,
    NotFoundError,
    RateLimitExceededError,
    UnprocessableStateError,
    ValidationError,
)

__all__ = [
    "AIOSError",
    "AuthenticationError",
    "AuthorizationError",
    "ConcurrentModificationError",
    "ConflictError",
    "ExternalServiceError",
    "NotFoundError",
    "RateLimitExceededError",
    "UnprocessableStateError",
    "ValidationError",
]
