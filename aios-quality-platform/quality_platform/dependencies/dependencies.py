"""FastAPI dependency wiring: DB session -> RepositoryRegistry ->
every service. Auth is intentionally minimal here, matching every
sibling AIOS platform: this platform expects to sit behind an
already-authenticated gateway (in practice, the Identity Platform)
that forwards the caller's tenant via `X-Tenant-Id` and, where
relevant, the acting principal via `X-User-Id`. Every service is
built fresh per request off a per-request `RepositoryRegistry`/
`AsyncSession`, since a session must never be shared across
concurrent requests."""
from __future__ import annotations

from collections.abc import AsyncGenerator

from fastapi import Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from quality_platform.ai_quality.baseline_service import BaselineService
from quality_platform.ai_quality.evaluation_service import EvaluationService
from quality_platform.ai_quality.regression_scan_service import RegressionScanService
from quality_platform.certification.certification_run_service import CertificationRunService
from quality_platform.chaos.chaos_experiment_service import ChaosExperimentService
from quality_platform.config.settings import Settings, get_settings
from quality_platform.database.session import session_scope
from quality_platform.failure_analysis.failure_pattern_service import FailurePatternService
from quality_platform.failure_analysis.risk_assessment_service import RiskAssessmentService
from quality_platform.observability.trend_service import TrendService
from quality_platform.performance.benchmark_result_service import BenchmarkResultService
from quality_platform.performance.performance_test_run_service import PerformanceTestRunService
from quality_platform.quality_gates.coverage_service import CoverageService
from quality_platform.quality_gates.quality_gate_service import QualityGateService
from quality_platform.reliability.reliability_snapshot_service import ReliabilitySnapshotService
from quality_platform.reliability.slo_service import SloService
from quality_platform.repositories.registry import RepositoryRegistry
from quality_platform.security_testing.security_scan_service import SecurityScanService
from quality_platform.testing.test_run_service import TestRunService
from quality_platform.testing.test_suite_service import TestSuiteService
from quality_platform.validation.api_validation_service import ApiValidationService
from quality_platform.validation.workflow_validation_service import WorkflowValidationRunService


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Delegates to `session_scope`, which commits on a clean exit and
    rolls back on any exception — a request handled through the REST
    API needs its writes to actually persist once the response is
    returned."""
    async for session in session_scope():
        yield session


async def get_repos(session: AsyncSession = Depends(get_session)) -> RepositoryRegistry:
    return RepositoryRegistry(session)


def get_settings_dep() -> Settings:
    return get_settings()


async def get_current_tenant_id(x_tenant_id: str | None = Header(default=None)) -> str:
    if not x_tenant_id:
        raise HTTPException(status_code=400, detail="Missing X-Tenant-Id header")
    return x_tenant_id


async def get_current_actor_id(x_user_id: str | None = Header(default=None)) -> str | None:
    """Unlike the tenant header, the actor header is optional — some of
    what this platform tracks (scheduled scans, automated certification
    runs, retention sweeps) legitimately comes from a process with no
    human actor behind it."""
    return x_user_id


# -- test management & automation (test pyramid) -------------------------------------------------------
async def get_test_suite_service(repos: RepositoryRegistry = Depends(get_repos)) -> TestSuiteService:
    return TestSuiteService(repos)


async def get_test_run_service(repos: RepositoryRegistry = Depends(get_repos)) -> TestRunService:
    return TestRunService(repos)


# -- AI quality / evaluation regression engine ----------------------------------------------------------
async def get_baseline_service(repos: RepositoryRegistry = Depends(get_repos)) -> BaselineService:
    return BaselineService(repos)


async def get_evaluation_service(repos: RepositoryRegistry = Depends(get_repos)) -> EvaluationService:
    return EvaluationService(repos)


async def get_regression_scan_service(repos: RepositoryRegistry = Depends(get_repos)) -> RegressionScanService:
    return RegressionScanService(repos)


# -- performance testing engine -------------------------------------------------------------------------
async def get_performance_test_run_service(repos: RepositoryRegistry = Depends(get_repos)) -> PerformanceTestRunService:
    return PerformanceTestRunService(repos)


async def get_benchmark_result_service(repos: RepositoryRegistry = Depends(get_repos)) -> BenchmarkResultService:
    return BenchmarkResultService(repos)


# -- chaos engineering platform --------------------------------------------------------------------------
async def get_chaos_experiment_service(repos: RepositoryRegistry = Depends(get_repos)) -> ChaosExperimentService:
    return ChaosExperimentService(repos)


# -- security testing engine -----------------------------------------------------------------------------
async def get_security_scan_service(repos: RepositoryRegistry = Depends(get_repos)) -> SecurityScanService:
    return SecurityScanService(repos)


# -- API & workflow validation ---------------------------------------------------------------------------
async def get_api_validation_service(repos: RepositoryRegistry = Depends(get_repos)) -> ApiValidationService:
    return ApiValidationService(repos)


async def get_workflow_validation_service(repos: RepositoryRegistry = Depends(get_repos)) -> WorkflowValidationRunService:
    return WorkflowValidationRunService(repos)


# -- reliability engineering -----------------------------------------------------------------------------
async def get_slo_service(repos: RepositoryRegistry = Depends(get_repos)) -> SloService:
    return SloService(repos)


async def get_reliability_snapshot_service(repos: RepositoryRegistry = Depends(get_repos)) -> ReliabilitySnapshotService:
    return ReliabilitySnapshotService(repos)


# -- quality gates & coverage platform --------------------------------------------------------------------
async def get_quality_gate_service(repos: RepositoryRegistry = Depends(get_repos)) -> QualityGateService:
    return QualityGateService(repos)


async def get_coverage_service(repos: RepositoryRegistry = Depends(get_repos)) -> CoverageService:
    return CoverageService(repos)


# -- failure analysis & risk analysis -----------------------------------------------------------------------
async def get_failure_pattern_service(repos: RepositoryRegistry = Depends(get_repos)) -> FailurePatternService:
    return FailurePatternService(repos)


async def get_risk_assessment_service(repos: RepositoryRegistry = Depends(get_repos)) -> RiskAssessmentService:
    return RiskAssessmentService(repos)


# -- release certification engine -----------------------------------------------------------------------------
async def get_certification_run_service(repos: RepositoryRegistry = Depends(get_repos)) -> CertificationRunService:
    return CertificationRunService(repos)


# -- observability -----------------------------------------------------------------------------------------
async def get_trend_service(repos: RepositoryRegistry = Depends(get_repos)) -> TrendService:
    return TrendService(repos)
