"""Application-wide exception hierarchy.

Every raised exception in the domain/application layers derives from
`AIOSError` so `app.core.exception_handlers` can translate any of them into
a consistent JSON error envelope without each router writing its own
try/except. Domain code should never raise a raw `HTTPException` — that
couples business logic to the web framework and is exactly the kind of
layering violation Clean Architecture exists to prevent.
"""


class AIOSError(Exception):
    """Base class for every application-defined error."""

    status_code: int = 500
    error_code: str = "internal_error"

    def __init__(self, message: str | None = None, **details):
        self.message = message or self.__class__.__doc__ or self.error_code
        self.details = details
        super().__init__(self.message)


class NotFoundError(AIOSError):
    """The requested resource does not exist."""

    status_code = 404
    error_code = "not_found"


class ValidationError(AIOSError):
    """The request failed a business-rule validation."""

    status_code = 422
    error_code = "validation_error"


class ConflictError(AIOSError):
    """The request conflicts with the current state of the resource."""

    status_code = 409
    error_code = "conflict"


class ConcurrentModificationError(ConflictError):
    """The resource was modified concurrently (optimistic lock failure)."""

    error_code = "concurrent_modification"


class AuthenticationError(AIOSError):
    """Authentication failed or credentials are missing/invalid."""

    status_code = 401
    error_code = "authentication_failed"


class AuthorizationError(AIOSError):
    """The authenticated principal lacks permission for this action."""

    status_code = 403
    error_code = "authorization_failed"


class RateLimitExceededError(AIOSError):
    """Too many requests in the current window."""

    status_code = 429
    error_code = "rate_limit_exceeded"


class UnprocessableStateError(AIOSError):
    """The action is not valid given the resource's current lifecycle state."""

    status_code = 422
    error_code = "invalid_state_transition"


class ExternalServiceError(AIOSError):
    """A downstream dependency (model provider, vector store, etc.) failed."""

    status_code = 502
    error_code = "external_service_error"
