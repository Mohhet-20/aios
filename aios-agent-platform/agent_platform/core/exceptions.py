"""Exception hierarchy for the Multi-Agent AI Platform."""
from __future__ import annotations


class AgentPlatformError(Exception):
    """Base class for every platform exception."""


class NotFoundError(AgentPlatformError):
    pass


class ValidationError(AgentPlatformError):
    pass


class ConflictError(AgentPlatformError):
    pass


class ConcurrentModificationError(AgentPlatformError):
    pass


class AuthorizationError(AgentPlatformError):
    pass


class InvalidTransitionError(AgentPlatformError):
    """Raised on an illegal agent/task lifecycle transition."""


class ApprovalRequiredError(AgentPlatformError):
    """Raised when an action requires human approval that hasn't happened."""


class DependencyCycleError(AgentPlatformError):
    """Raised when a task dependency graph would contain a cycle."""


class RecursionLimitExceededError(AgentPlatformError):
    """Raised when delegation/decomposition would exceed the configured
    max recursion depth — the hard ceiling that keeps a buggy or
    adversarial plan from recursing unboundedly."""


class ResourceQuotaExceededError(AgentPlatformError):
    """Raised when an agent/workspace exceeds its concurrency, rate, or
    resource quota."""


class ToolPermissionError(AgentPlatformError):
    """Raised when an agent attempts to use a tool it isn't permitted to."""


class OrchestrationError(AgentPlatformError):
    """Raised on an orchestration-level failure (e.g. all delegates failed,
    consensus not reached)."""


class ExecutionCancelledError(AgentPlatformError):
    """Raised when an interruptible execution is cancelled mid-flight."""
