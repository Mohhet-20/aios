"""Domain exception hierarchy for the Enterprise Testing, Quality
Engineering & Reliability Platform."""
from __future__ import annotations


class QualityPlatformError(Exception):
    pass


class NotFoundError(QualityPlatformError):
    pass


class ValidationError(QualityPlatformError):
    pass


class ConflictError(QualityPlatformError):
    pass


class ConcurrentModificationError(QualityPlatformError):
    pass


class AuthorizationError(QualityPlatformError):
    pass


class PermissionDeniedError(AuthorizationError):
    pass


class TenantIsolationError(AuthorizationError):
    pass


class InvalidTransitionError(QualityPlatformError):
    pass


# -- test management & automation -------------------------------------------------------------------

class TestingError(QualityPlatformError):
    pass


class TestSuiteNotFoundError(TestingError):
    pass


class TestCaseNotFoundError(TestingError):
    pass


class TestRunNotFoundError(TestingError):
    pass


class UnsupportedTestTypeError(TestingError):
    pass


# -- AI quality / evaluation regression engine --------------------------------------------------------

class AiQualityError(QualityPlatformError):
    pass


class UnsupportedAiQualityDimensionError(AiQualityError):
    pass


class AiQualityBaselineNotFoundError(AiQualityError):
    pass


class RegressionDetectedError(AiQualityError):
    pass


# -- performance testing engine ------------------------------------------------------------------------

class PerformanceTestingError(QualityPlatformError):
    pass


class UnsupportedPerformanceTestTypeError(PerformanceTestingError):
    pass


class PerformanceTestRunNotFoundError(PerformanceTestingError):
    pass


class BenchmarkNotFoundError(PerformanceTestingError):
    pass


# -- chaos engineering platform -------------------------------------------------------------------------

class ChaosError(QualityPlatformError):
    pass


class UnsupportedFailureTypeError(ChaosError):
    pass


class ChaosExperimentNotFoundError(ChaosError):
    pass


class BlastRadiusExceededError(ChaosError):
    pass


# -- security testing engine -----------------------------------------------------------------------------

class SecurityTestingError(QualityPlatformError):
    pass


class UnsupportedSecurityTestTypeError(SecurityTestingError):
    pass


class SecurityScanNotFoundError(SecurityTestingError):
    pass


# -- API & workflow validation -----------------------------------------------------------------------------

class ApiValidationError(QualityPlatformError):
    pass


class UnsupportedApiValidationTypeError(ApiValidationError):
    pass


class WorkflowValidationError(QualityPlatformError):
    pass


class WorkflowValidationRunNotFoundError(WorkflowValidationError):
    pass


# -- reliability engineering --------------------------------------------------------------------------------

class ReliabilityError(QualityPlatformError):
    pass


class SloNotFoundError(ReliabilityError):
    pass


class UnsupportedReliabilityMetricError(ReliabilityError):
    pass


# -- quality gates & coverage platform --------------------------------------------------------------------------

class QualityGateError(QualityPlatformError):
    pass


class QualityGateNotFoundError(QualityGateError):
    pass


class QualityGateFailedError(QualityGateError):
    pass


class CoverageError(QualityPlatformError):
    pass


class UnsupportedCoverageTypeError(CoverageError):
    pass


# -- failure analysis & risk analysis -------------------------------------------------------------------------------

class FailureAnalysisError(QualityPlatformError):
    pass


class FailurePatternNotFoundError(FailureAnalysisError):
    pass


class RiskAssessmentNotFoundError(FailureAnalysisError):
    pass


# -- release certification engine -----------------------------------------------------------------------------------

class CertificationError(QualityPlatformError):
    pass


class CertificationRunNotFoundError(CertificationError):
    pass


class CertificationGenerationFailedError(CertificationError):
    pass


# -- observability --------------------------------------------------------------------------------------------------

class ObservabilityError(QualityPlatformError):
    pass


class TrendSnapshotNotFoundError(ObservabilityError):
    pass
