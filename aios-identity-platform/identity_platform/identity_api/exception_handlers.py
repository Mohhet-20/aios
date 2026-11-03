"""Maps the platform's domain exception hierarchy (core/exceptions.py) to
HTTP status codes, so every service can keep raising plain Python
exceptions without knowing anything about HTTP — routers never need a
try/except block either. Order matters: this is checked top-to-bottom,
so subclasses are listed before their parent class."""
from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from identity_platform.core.exceptions import (
    AccountLockedError,
    AccountNotVerifiedError,
    AnomalyDetectedError,
    ApiKeyExpiredError,
    ApiKeyRevokedError,
    ApiKeyError,
    AuthorizationError,
    ConcurrentModificationError,
    ConcurrentSessionLimitExceededError,
    ConflictError,
    FederatedIdentityError,
    IdentityPlatformError,
    InvalidCredentialsError,
    InvalidMfaCodeError,
    InvalidTransitionError,
    InvitationExpiredError,
    InvitationError,
    MembershipError,
    MfaRequiredError,
    MfaError,
    NotFoundError,
    OrganizationError,
    PasswordPolicyError,
    PermissionDeniedError,
    PolicyError,
    ProjectError,
    QuotaExceededError,
    RateLimitExceededError,
    RecoveryCodeExhaustedError,
    RoleError,
    ServiceAccountError,
    SessionExpiredError,
    SessionRevokedError,
    SessionError,
    TeamError,
    TenantIsolationError,
    TokenAlreadyUsedError,
    TokenExpiredError,
    TokenError,
    UnknownIdentityProviderError,
    UnknownPermissionError,
    ValidationError,
    WorkspaceError,
)

_STATUS_BY_EXCEPTION: list[tuple[type[IdentityPlatformError], int]] = [
    (NotFoundError, 404),
    (InvalidCredentialsError, 401),
    (AccountLockedError, 423),
    (AccountNotVerifiedError, 403),
    (PasswordPolicyError, 422),
    (TokenAlreadyUsedError, 409),
    (TokenExpiredError, 401),
    (TokenError, 401),
    (MfaRequiredError, 401),
    (InvalidMfaCodeError, 401),
    (RecoveryCodeExhaustedError, 400),
    (MfaError, 400),
    (SessionExpiredError, 401),
    (SessionRevokedError, 401),
    (ConcurrentSessionLimitExceededError, 429),
    (SessionError, 401),
    (UnknownIdentityProviderError, 400),
    (FederatedIdentityError, 502),
    (InvitationExpiredError, 410),
    (InvitationError, 400),
    (MembershipError, 409),
    (OrganizationError, 400),
    (WorkspaceError, 400),
    (TeamError, 400),
    (ProjectError, 400),
    (UnknownPermissionError, 400),
    (PermissionDeniedError, 403),
    (RoleError, 400),
    (TenantIsolationError, 403),
    (QuotaExceededError, 429),
    (ApiKeyExpiredError, 401),
    (ApiKeyRevokedError, 401),
    (ApiKeyError, 400),
    (ServiceAccountError, 400),
    (RateLimitExceededError, 429),
    (AnomalyDetectedError, 403),
    (PolicyError, 400),
    (AuthorizationError, 403),
    (ConflictError, 409),
    (ConcurrentModificationError, 409),
    (InvalidTransitionError, 409),
    (ValidationError, 422),
]


def _status_for(exc: IdentityPlatformError) -> int:
    for exc_type, status_code in _STATUS_BY_EXCEPTION:
        if isinstance(exc, exc_type):
            return status_code
    return 400


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(IdentityPlatformError)
    async def _handle_platform_error(request: Request, exc: IdentityPlatformError) -> JSONResponse:
        return JSONResponse(status_code=_status_for(exc), content={"error": exc.__class__.__name__, "detail": str(exc)})
