"""Exception hierarchy for the Tool Execution & Integration Platform."""
from __future__ import annotations


class ToolPlatformError(Exception):
    """Base class for every platform exception."""


class NotFoundError(ToolPlatformError):
    pass


class ValidationError(ToolPlatformError):
    pass


class ConflictError(ToolPlatformError):
    pass


class ConcurrentModificationError(ToolPlatformError):
    pass


class AuthorizationError(ToolPlatformError):
    pass


class InvalidTransitionError(ToolPlatformError):
    """Raised on an illegal tool/execution/plugin/credential lifecycle transition."""


class SchemaValidationError(ValidationError):
    """Raised when tool call input/output fails validation against its declared schema."""


class ToolExecutionError(ToolPlatformError):
    """Raised when a tool's handler fails in a way the engine needs to know about."""


class ToolTimeoutError(ToolExecutionError):
    pass


class RetryExhaustedError(ToolExecutionError):
    """Raised when a tool call has exhausted its configured retry attempts."""


class CheckpointError(ToolPlatformError):
    pass


class SandboxViolationError(ToolExecutionError):
    """Raised when a sandboxed execution exceeds a resource limit or violates
    a network/filesystem policy."""


class ResourceLimitExceededError(SandboxViolationError):
    pass


class NetworkPolicyViolationError(SandboxViolationError):
    pass


class CredentialError(ToolPlatformError):
    pass


class CredentialExpiredError(CredentialError):
    pass


class CredentialNotFoundError(CredentialError, NotFoundError):
    pass


class PluginError(ToolPlatformError):
    pass


class PluginDependencyError(PluginError):
    pass


class PluginSignatureError(PluginError):
    """Raised when a plugin fails signature verification."""


class PluginIsolationError(PluginError):
    pass


class ConcurrencyLimitExceededError(ToolPlatformError):
    pass


class RateLimitExceededError(ToolPlatformError):
    pass


class ApprovalRequiredError(ToolPlatformError):
    """Raised (informationally) when a sensitive tool call pauses awaiting human approval."""


class UnknownToolTypeError(ToolPlatformError):
    pass


class ToolPlanningError(ToolPlatformError):
    """Raised when AI tool planning cannot find or compose a valid plan."""
