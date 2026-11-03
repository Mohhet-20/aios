"""Exception hierarchy for the Workflow Orchestration Engine."""
from __future__ import annotations


class WorkflowPlatformError(Exception):
    """Base class for every platform exception."""


class NotFoundError(WorkflowPlatformError):
    pass


class ValidationError(WorkflowPlatformError):
    pass


class ConflictError(WorkflowPlatformError):
    pass


class ConcurrentModificationError(WorkflowPlatformError):
    pass


class AuthorizationError(WorkflowPlatformError):
    pass


class InvalidTransitionError(WorkflowPlatformError):
    """Raised on an illegal workflow/execution/approval/schedule lifecycle transition."""


class WorkflowCycleError(WorkflowPlatformError):
    """Raised when a workflow graph contains an illegal cycle outside of a
    designated Loop node."""


class RecursionLimitExceededError(WorkflowPlatformError):
    """Raised when nested/recursive workflow invocation exceeds the configured depth."""


class NodeExecutionError(WorkflowPlatformError):
    """Raised when a node's handler fails in a way the engine needs to know about."""


class NodeTimeoutError(NodeExecutionError):
    pass


class RetryExhaustedError(NodeExecutionError):
    """Raised when a node has exhausted its configured retry attempts."""


class CompensationError(WorkflowPlatformError):
    """Raised when a rollback/compensation action itself fails."""


class CheckpointError(WorkflowPlatformError):
    pass


class ApprovalRequiredError(WorkflowPlatformError):
    """Raised (informationally) when execution pauses awaiting human approval."""


class ApprovalDeniedError(WorkflowPlatformError):
    pass


class ScheduleError(WorkflowPlatformError):
    pass


class ConcurrencyLimitExceededError(WorkflowPlatformError):
    pass


class RateLimitExceededError(WorkflowPlatformError):
    pass


class WebhookDeliveryError(WorkflowPlatformError):
    pass


class UnknownNodeTypeError(WorkflowPlatformError):
    pass


class VariableResolutionError(WorkflowPlatformError):
    pass
