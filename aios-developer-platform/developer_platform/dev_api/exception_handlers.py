"""Maps the platform's domain exception hierarchy (core/exceptions.py)
to HTTP status codes, so every service can keep raising plain Python
exceptions without knowing anything about HTTP — routers never need a
try/except block either. Order matters: this is checked top-to-bottom,
so subclasses are listed before their parent class."""
from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from developer_platform.core.exceptions import (
    AnalyticsError,
    ApiError,
    ApiKeyExpiredError,
    ApiKeyNotFoundError,
    ApiKeyRevokedError,
    AuthorizationError,
    CliError,
    CliNotAuthenticatedError,
    CliSessionExpiredError,
    CodeGenError,
    CodeGenJobFailedError,
    CodeGenUnsupportedTargetError,
    ConcurrentModificationError,
    ConflictError,
    CredentialExposedError,
    DevSecurityError,
    DeveloperPlatformError,
    ExtensionError,
    ExtensionPointNotFoundError,
    ExtensionRegistrationError,
    InvalidTransitionError,
    McpError,
    McpPermissionDeniedError,
    McpResourceNotFoundError,
    McpSessionExpiredError,
    McpSessionNotFoundError,
    NotFoundError,
    PackageDeprecatedError,
    PackageNotFoundError,
    PackageVersionExistsError,
    PermissionDeniedError,
    PluginAlreadyPublishedError,
    PluginDependencyError,
    PluginError,
    PluginNotFoundError,
    PluginSigningRequiredError,
    PluginValidationError,
    PortalError,
    RateLimitExceededError,
    RegistryError,
    SandboxExpiredError,
    SandboxLimitExceededError,
    SandboxNotFoundError,
    SdkError,
    SdkPackageNotFoundError,
    SdkVersionIncompatibleError,
    TenantIsolationError,
    UnsupportedApiVersionError,
    UnsupportedLanguageError,
    ValidationError,
    WebhookDeliveryFailedError,
    WebhookError,
    WebhookNotFoundError,
    WebhookSignatureError,
)

_STATUS_BY_EXCEPTION: list[tuple[type[DeveloperPlatformError], int]] = [
    (NotFoundError, 404),
    # api platform
    (ApiKeyNotFoundError, 404),
    (ApiKeyRevokedError, 401),
    (ApiKeyExpiredError, 401),
    (RateLimitExceededError, 429),
    (UnsupportedApiVersionError, 400),
    (ApiError, 400),
    # sdk platform
    (SdkPackageNotFoundError, 404),
    (SdkVersionIncompatibleError, 409),
    (UnsupportedLanguageError, 422),
    (SdkError, 400),
    # cli platform
    (CliSessionExpiredError, 401),
    (CliNotAuthenticatedError, 401),
    (CliError, 400),
    # plugin sdk
    (PluginNotFoundError, 404),
    (PluginValidationError, 422),
    (PluginSigningRequiredError, 403),
    (PluginAlreadyPublishedError, 409),
    (PluginDependencyError, 409),
    (PluginError, 400),
    # extension framework
    (ExtensionPointNotFoundError, 404),
    (ExtensionRegistrationError, 409),
    (ExtensionError, 400),
    # webhook platform
    (WebhookNotFoundError, 404),
    (WebhookDeliveryFailedError, 422),
    (WebhookSignatureError, 401),
    (WebhookError, 400),
    # mcp integration
    (McpSessionNotFoundError, 404),
    (McpResourceNotFoundError, 404),
    (McpSessionExpiredError, 401),
    (McpPermissionDeniedError, 403),
    (McpError, 400),
    # code generation
    (CodeGenUnsupportedTargetError, 422),
    (CodeGenJobFailedError, 422),
    (CodeGenError, 400),
    # developer portal / sandbox
    (SandboxLimitExceededError, 429),
    (SandboxNotFoundError, 404),
    (SandboxExpiredError, 410),
    (PortalError, 400),
    # package registry
    (PackageNotFoundError, 404),
    (PackageVersionExistsError, 409),
    (PackageDeprecatedError, 409),
    (RegistryError, 400),
    # developer analytics
    (AnalyticsError, 400),
    # security
    (CredentialExposedError, 403),
    (DevSecurityError, 400),
    # base group
    (TenantIsolationError, 403),
    (PermissionDeniedError, 403),
    (AuthorizationError, 403),
    (ConflictError, 409),
    (ConcurrentModificationError, 409),
    (InvalidTransitionError, 409),
    (ValidationError, 422),
]


def _status_for(exc: DeveloperPlatformError) -> int:
    for exc_type, status_code in _STATUS_BY_EXCEPTION:
        if isinstance(exc, exc_type):
            return status_code
    return 400


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(DeveloperPlatformError)
    async def _handle_platform_error(request: Request, exc: DeveloperPlatformError) -> JSONResponse:
        return JSONResponse(status_code=_status_for(exc), content={"error": exc.__class__.__name__, "detail": str(exc)})
