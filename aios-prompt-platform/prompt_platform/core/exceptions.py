"""Exception hierarchy for the Prompt Engineering Platform."""
from __future__ import annotations


class PromptPlatformError(Exception):
    """Base class for every platform exception."""


class NotFoundError(PromptPlatformError):
    pass


class ValidationError(PromptPlatformError):
    pass


class ConflictError(PromptPlatformError):
    pass


class ConcurrentModificationError(PromptPlatformError):
    pass


class AuthorizationError(PromptPlatformError):
    pass


class InvalidTransitionError(PromptPlatformError):
    """Raised on an illegal prompt lifecycle/version status transition."""


class ApprovalRequiredError(PromptPlatformError):
    """Raised when an action requires an approval that hasn't happened."""


class EvalGateNotMetError(PromptPlatformError):
    """Raised when promoting a version to production without meeting the
    minimum evaluation score gate."""

    def __init__(self, message: str, *, required: float, actual: float | None):
        super().__init__(message)
        self.required = required
        self.actual = actual


class SecurityViolationError(PromptPlatformError):
    """Raised when a prompt fails injection/sanitization checks."""


class DependencyCycleError(PromptPlatformError):
    pass


class DeploymentError(PromptPlatformError):
    pass
