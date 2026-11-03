"""Maps the platform's domain exception hierarchy (core/exceptions.py)
to HTTP status codes, so every service can keep raising plain Python
exceptions without knowing anything about HTTP — routers never need a
try/except block either. Order matters: this is checked top-to-bottom,
so subclasses are listed before their parent class."""
from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from quality_platform.core.exceptions import (
    AiQualityBaselineNotFoundError,
    AiQualityError,
    ApiValidationError,
    AuthorizationError,
    BenchmarkNotFoundError,
    BlastRadiusExceededError,
    CertificationError,
    CertificationGenerationFailedError,
    CertificationRunNotFoundError,
    ChaosError,
    ChaosExperimentNotFoundError,
    ConcurrentModificationError,
    ConflictError,
    CoverageError,
    FailureAnalysisError,
    FailurePatternNotFoundError,
    InvalidTransitionError,
    NotFoundError,
    ObservabilityError,
    PerformanceTestingError,
    PerformanceTestRunNotFoundError,
    PermissionDeniedError,
    QualityGateError,
    QualityGateFailedError,
    QualityGateNotFoundError,
    QualityPlatformError,
    RegressionDetectedError,
    ReliabilityError,
    RiskAssessmentNotFoundError,
    SecurityScanNotFoundError,
    SecurityTestingError,
    SloNotFoundError,
    TenantIsolationError,
    TestCaseNotFoundError,
    TestingError,
    TestRunNotFoundError,
    TestSuiteNotFoundError,
    TrendSnapshotNotFoundError,
    UnsupportedAiQualityDimensionError,
    UnsupportedApiValidationTypeError,
    UnsupportedCoverageTypeError,
    UnsupportedFailureTypeError,
    UnsupportedPerformanceTestTypeError,
    UnsupportedReliabilityMetricError,
    UnsupportedSecurityTestTypeError,
    UnsupportedTestTypeError,
    ValidationError,
    WorkflowValidationError,
    WorkflowValidationRunNotFoundError,
)

_STATUS_BY_EXCEPTION: list[tuple[type[QualityPlatformError], int]] = [
    (NotFoundError, 404),
    # test management & automation
    (TestSuiteNotFoundError, 404),
    (TestCaseNotFoundError, 404),
    (TestRunNotFoundError, 404),
    (UnsupportedTestTypeError, 422),
    (TestingError, 400),
    # AI quality / evaluation regression engine
    (AiQualityBaselineNotFoundError, 404),
    (UnsupportedAiQualityDimensionError, 422),
    (RegressionDetectedError, 422),
    (AiQualityError, 400),
    # performance testing engine
    (PerformanceTestRunNotFoundError, 404),
    (BenchmarkNotFoundError, 404),
    (UnsupportedPerformanceTestTypeError, 422),
    (PerformanceTestingError, 400),
    # chaos engineering platform
    (ChaosExperimentNotFoundError, 404),
    (UnsupportedFailureTypeError, 422),
    (BlastRadiusExceededError, 422),
    (ChaosError, 400),
    # security testing engine
    (SecurityScanNotFoundError, 404),
    (UnsupportedSecurityTestTypeError, 422),
    (SecurityTestingError, 400),
    # API & workflow validation
    (WorkflowValidationRunNotFoundError, 404),
    (UnsupportedApiValidationTypeError, 422),
    (WorkflowValidationError, 400),
    (ApiValidationError, 400),
    # reliability engineering
    (SloNotFoundError, 404),
    (UnsupportedReliabilityMetricError, 422),
    (ReliabilityError, 400),
    # quality gates & coverage platform
    (QualityGateNotFoundError, 404),
    (QualityGateFailedError, 422),
    (UnsupportedCoverageTypeError, 422),
    (CoverageError, 400),
    (QualityGateError, 400),
    # failure analysis & risk analysis
    (FailurePatternNotFoundError, 404),
    (RiskAssessmentNotFoundError, 404),
    (FailureAnalysisError, 400),
    # release certification engine
    (CertificationRunNotFoundError, 404),
    (CertificationGenerationFailedError, 422),
    (CertificationError, 400),
    # observability
    (TrendSnapshotNotFoundError, 404),
    (ObservabilityError, 400),
    # common group
    (TenantIsolationError, 403),
    (PermissionDeniedError, 403),
    (AuthorizationError, 403),
    (ConflictError, 409),
    (ConcurrentModificationError, 409),
    (InvalidTransitionError, 409),
    (ValidationError, 422),
]


def _status_for(exc: QualityPlatformError) -> int:
    for exc_type, status_code in _STATUS_BY_EXCEPTION:
        if isinstance(exc, exc_type):
            return status_code
    return 400


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(QualityPlatformError)
    async def _handle_platform_error(request: Request, exc: QualityPlatformError) -> JSONResponse:
        return JSONResponse(status_code=_status_for(exc), content={"error": exc.__class__.__name__, "detail": str(exc)})
