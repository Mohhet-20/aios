"""Exception hierarchy for the Enterprise Developer Platform & SDK
Ecosystem."""
from __future__ import annotations


class DeveloperPlatformError(Exception):
    """Base class for every platform exception."""


class NotFoundError(DeveloperPlatformError):
    pass


class ValidationError(DeveloperPlatformError):
    pass


class ConflictError(DeveloperPlatformError):
    pass


class ConcurrentModificationError(DeveloperPlatformError):
    pass


class AuthorizationError(DeveloperPlatformError):
    pass


class PermissionDeniedError(AuthorizationError):
    pass


class TenantIsolationError(AuthorizationError):
    pass


class InvalidTransitionError(DeveloperPlatformError):
    """Raised on an illegal lifecycle transition (plugin, webhook
    delivery, package version, MCP session, code-gen job, API key)."""


# -- api platform -------------------------------------------------------------------------------

class ApiError(DeveloperPlatformError):
    pass


class ApiKeyNotFoundError(ApiError):
    pass


class ApiKeyRevokedError(ApiError):
    pass


class ApiKeyExpiredError(ApiError):
    pass


class RateLimitExceededError(ApiError):
    pass


class UnsupportedApiVersionError(ApiError):
    pass


# -- sdk platform -------------------------------------------------------------------------------

class SdkError(DeveloperPlatformError):
    pass


class SdkPackageNotFoundError(SdkError):
    pass


class SdkVersionIncompatibleError(SdkError):
    pass


class UnsupportedLanguageError(SdkError):
    pass


# -- cli platform -------------------------------------------------------------------------------

class CliError(DeveloperPlatformError):
    pass


class CliSessionExpiredError(CliError):
    pass


class CliNotAuthenticatedError(CliError):
    pass


# -- plugin sdk ---------------------------------------------------------------------------------

class PluginError(DeveloperPlatformError):
    pass


class PluginNotFoundError(PluginError):
    pass


class PluginValidationError(PluginError):
    pass


class PluginSigningRequiredError(PluginError):
    pass


class PluginAlreadyPublishedError(PluginError):
    pass


class PluginDependencyError(PluginError):
    pass


# -- extension framework ------------------------------------------------------------------------

class ExtensionError(DeveloperPlatformError):
    pass


class ExtensionPointNotFoundError(ExtensionError):
    pass


class ExtensionRegistrationError(ExtensionError):
    pass


# -- webhook platform ---------------------------------------------------------------------------

class WebhookError(DeveloperPlatformError):
    pass


class WebhookNotFoundError(WebhookError):
    pass


class WebhookDeliveryFailedError(WebhookError):
    pass


class WebhookSignatureError(WebhookError):
    pass


# -- mcp integration ----------------------------------------------------------------------------

class McpError(DeveloperPlatformError):
    pass


class McpSessionNotFoundError(McpError):
    pass


class McpSessionExpiredError(McpError):
    pass


class McpPermissionDeniedError(McpError):
    pass


class McpResourceNotFoundError(McpError):
    pass


# -- code generation ----------------------------------------------------------------------------

class CodeGenError(DeveloperPlatformError):
    pass


class CodeGenUnsupportedTargetError(CodeGenError):
    pass


class CodeGenJobFailedError(CodeGenError):
    pass


# -- developer portal / sandbox -----------------------------------------------------------------

class PortalError(DeveloperPlatformError):
    pass


class SandboxLimitExceededError(PortalError):
    pass


class SandboxNotFoundError(PortalError):
    pass


class SandboxExpiredError(PortalError):
    pass


# -- package registry ---------------------------------------------------------------------------

class RegistryError(DeveloperPlatformError):
    pass


class PackageNotFoundError(RegistryError):
    pass


class PackageVersionExistsError(RegistryError):
    pass


class PackageDeprecatedError(RegistryError):
    pass


# -- developer analytics ------------------------------------------------------------------------

class AnalyticsError(DeveloperPlatformError):
    pass


# -- security -------------------------------------------------------------------------------------

class DevSecurityError(DeveloperPlatformError):
    pass


class CredentialExposedError(DevSecurityError):
    pass
