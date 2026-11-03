"""Unit-of-work: lazily builds and memoizes one repository per model,
all sharing a single `AsyncSession` (and therefore the same
transaction) for the lifetime of a request or test."""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from quality_platform.repositories.ai_quality_repository import (
    AiQualityBaselineRepository,
    AiQualityEvaluationRepository,
    RegressionScanRepository,
)
from quality_platform.repositories.certification_repository import CertificationRunRepository
from quality_platform.repositories.chaos_repository import ChaosExperimentRepository
from quality_platform.repositories.failure_analysis_repository import FailurePatternRepository, RiskAssessmentRepository
from quality_platform.repositories.observability_repository import TrendSnapshotRepository
from quality_platform.repositories.performance_repository import BenchmarkResultRepository, PerformanceTestRunRepository
from quality_platform.repositories.quality_gates_repository import (
    CoverageSnapshotRepository,
    QualityGateCheckResultRepository,
    QualityGateRepository,
)
from quality_platform.repositories.reliability_repository import ReliabilityMetricSnapshotRepository, SloDefinitionRepository
from quality_platform.repositories.security_testing_repository import SecurityFindingRepository, SecurityScanRepository
from quality_platform.repositories.testing_repository import (
    TestCaseRepository,
    TestCaseResultRepository,
    TestRunRepository,
    TestSuiteRepository,
)
from quality_platform.repositories.validation_repository import ApiValidationRunRepository, WorkflowValidationRunRepository


class RepositoryRegistry:
    def __init__(self, session: AsyncSession):
        self.session = session
        self._repos: dict[str, object] = {}

    def _get(self, key: str, cls: type) -> object:
        if key not in self._repos:
            self._repos[key] = cls(self.session)
        return self._repos[key]

    # -- test management & automation --
    @property
    def test_suites(self) -> TestSuiteRepository:
        return self._get("test_suites", TestSuiteRepository)

    @property
    def test_cases(self) -> TestCaseRepository:
        return self._get("test_cases", TestCaseRepository)

    @property
    def test_runs(self) -> TestRunRepository:
        return self._get("test_runs", TestRunRepository)

    @property
    def test_case_results(self) -> TestCaseResultRepository:
        return self._get("test_case_results", TestCaseResultRepository)

    # -- AI quality / evaluation regression engine --
    @property
    def ai_quality_baselines(self) -> AiQualityBaselineRepository:
        return self._get("ai_quality_baselines", AiQualityBaselineRepository)

    @property
    def ai_quality_evaluations(self) -> AiQualityEvaluationRepository:
        return self._get("ai_quality_evaluations", AiQualityEvaluationRepository)

    @property
    def regression_scans(self) -> RegressionScanRepository:
        return self._get("regression_scans", RegressionScanRepository)

    # -- performance testing engine --
    @property
    def performance_test_runs(self) -> PerformanceTestRunRepository:
        return self._get("performance_test_runs", PerformanceTestRunRepository)

    @property
    def benchmark_results(self) -> BenchmarkResultRepository:
        return self._get("benchmark_results", BenchmarkResultRepository)

    # -- chaos engineering platform --
    @property
    def chaos_experiments(self) -> ChaosExperimentRepository:
        return self._get("chaos_experiments", ChaosExperimentRepository)

    # -- security testing engine --
    @property
    def security_scans(self) -> SecurityScanRepository:
        return self._get("security_scans", SecurityScanRepository)

    @property
    def security_findings(self) -> SecurityFindingRepository:
        return self._get("security_findings", SecurityFindingRepository)

    # -- API & workflow validation --
    @property
    def api_validation_runs(self) -> ApiValidationRunRepository:
        return self._get("api_validation_runs", ApiValidationRunRepository)

    @property
    def workflow_validation_runs(self) -> WorkflowValidationRunRepository:
        return self._get("workflow_validation_runs", WorkflowValidationRunRepository)

    # -- reliability engineering --
    @property
    def slo_definitions(self) -> SloDefinitionRepository:
        return self._get("slo_definitions", SloDefinitionRepository)

    @property
    def reliability_snapshots(self) -> ReliabilityMetricSnapshotRepository:
        return self._get("reliability_snapshots", ReliabilityMetricSnapshotRepository)

    # -- quality gates & coverage platform --
    @property
    def quality_gates(self) -> QualityGateRepository:
        return self._get("quality_gates", QualityGateRepository)

    @property
    def quality_gate_check_results(self) -> QualityGateCheckResultRepository:
        return self._get("quality_gate_check_results", QualityGateCheckResultRepository)

    @property
    def coverage_snapshots(self) -> CoverageSnapshotRepository:
        return self._get("coverage_snapshots", CoverageSnapshotRepository)

    # -- failure analysis & risk analysis --
    @property
    def failure_patterns(self) -> FailurePatternRepository:
        return self._get("failure_patterns", FailurePatternRepository)

    @property
    def risk_assessments(self) -> RiskAssessmentRepository:
        return self._get("risk_assessments", RiskAssessmentRepository)

    # -- release certification engine --
    @property
    def certification_runs(self) -> CertificationRunRepository:
        return self._get("certification_runs", CertificationRunRepository)

    # -- observability --
    @property
    def trend_snapshots(self) -> TrendSnapshotRepository:
        return self._get("trend_snapshots", TrendSnapshotRepository)
