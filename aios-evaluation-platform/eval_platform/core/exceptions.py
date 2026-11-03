"""Exception hierarchy for the Enterprise AI Evaluation, Benchmarking &
Observability Platform."""
from __future__ import annotations


class EvalPlatformError(Exception):
    """Base class for every platform exception."""


class NotFoundError(EvalPlatformError):
    pass


class ValidationError(EvalPlatformError):
    pass


class ConflictError(EvalPlatformError):
    pass


class ConcurrentModificationError(EvalPlatformError):
    pass


class AuthorizationError(EvalPlatformError):
    pass


class InvalidTransitionError(EvalPlatformError):
    """Raised on an illegal evaluation/run/dataset/alert lifecycle transition."""


class SchemaValidationError(ValidationError):
    """Raised when a structured-output evaluation's actual output fails
    validation against its declared JSON Schema."""


class EvaluationExecutionError(EvalPlatformError):
    """Raised when an evaluation run fails in a way the engine needs to know about."""


class EvaluationTimeoutError(EvaluationExecutionError):
    pass


class RetryExhaustedError(EvaluationExecutionError):
    pass


class MetricComputationError(EvalPlatformError):
    """Raised when a metric function cannot be computed for the given inputs
    (e.g. missing required fields), never silently returning a fabricated score."""


class UnknownMetricError(EvalPlatformError):
    pass


class UnknownEvaluationTypeError(EvalPlatformError):
    pass


class DatasetError(EvalPlatformError):
    pass


class DatasetVersionError(DatasetError):
    pass


class BenchmarkError(EvalPlatformError):
    pass


class HallucinationCheckError(EvalPlatformError):
    pass


class AlertRuleError(EvalPlatformError):
    pass


class ConcurrencyLimitExceededError(EvalPlatformError):
    pass


class RateLimitExceededError(EvalPlatformError):
    pass


class ApprovalRequiredError(EvalPlatformError):
    """Raised (informationally) when a sensitive evaluation/report action pauses awaiting human approval."""


class RecommendationError(EvalPlatformError):
    pass
