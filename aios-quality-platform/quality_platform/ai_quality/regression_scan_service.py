"""Regression scan job lifecycle: request_scan() enqueues a scan
against a (dimension, subject_ref) pair, start()/complete()/fail()
drive the guarded queued -> running -> completed/failed transitions on
the domain-level `RegressionScan` entity, and run_scan() is the
convenience orchestrator that pulls the stored baseline and the most
recent evaluation, classifies drift via `regression_rules`, and
completes (or fails, if no baseline/evaluation exists yet) the scan.
`assert_no_regression` is a separate strict check callers such as a
future quality gate can use to turn a major/critical finding into a
hard failure rather than just a recorded severity."""
from __future__ import annotations


from quality_platform.ai_quality.baseline_service import BaselineService
from quality_platform.ai_quality.evaluation_service import EvaluationService
from quality_platform.ai_quality.regression_rules import classify_regression
from quality_platform.config.settings import get_settings
from quality_platform.core.exceptions import (
    AiQualityBaselineNotFoundError,
    InvalidTransitionError,
    RegressionDetectedError,
    UnsupportedAiQualityDimensionError,
)
from quality_platform.domain.entities import RegressionScan
from quality_platform.domain.enums import JobStatus, RegressionSeverity
from quality_platform.models.ai_quality import RegressionScanModel
from quality_platform.repositories.registry import RepositoryRegistry
from quality_platform.clock import utc_now


class RegressionScanService:
    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos
        self.settings = get_settings()
        self.baselines = BaselineService(repos)
        self.evaluations = EvaluationService(repos)

    async def get_or_404(self, tenant_id: str, scan_id: str) -> RegressionScanModel:
        scan = await self.repos.regression_scans.get_or_404(scan_id)
        if scan.tenant_id != tenant_id:
            raise AiQualityBaselineNotFoundError(f"Regression scan '{scan_id}' not found for tenant '{tenant_id}'")
        return scan

    async def request_scan(self, tenant_id: str, dimension: str, subject_ref: str) -> RegressionScanModel:
        if dimension not in self.settings.ai_quality_dimensions:
            raise UnsupportedAiQualityDimensionError(f"Unsupported AI quality dimension '{dimension}'")
        scan = RegressionScanModel(tenant_id=tenant_id, dimension=dimension, subject_ref=subject_ref, status=JobStatus.QUEUED.value)
        return await self.repos.regression_scans.add(scan)

    async def _apply_transition(self, tenant_id: str, scan_id: str, transition_name: str) -> RegressionScanModel:
        scan = await self.get_or_404(tenant_id, scan_id)
        entity = RegressionScan(id=scan.id, status=JobStatus(scan.status))
        try:
            getattr(entity, transition_name)()
        except InvalidTransitionError:
            raise
        scan.status = entity.status.value
        return scan

    async def start(self, tenant_id: str, scan_id: str) -> RegressionScanModel:
        scan = await self._apply_transition(tenant_id, scan_id, "start")
        return await self.repos.regression_scans.update(scan)

    async def complete(
        self, tenant_id: str, scan_id: str, *, baseline_score: float, current_score: float,
        delta_pct: float, severity: RegressionSeverity, result: dict,
    ) -> RegressionScanModel:
        scan = await self._apply_transition(tenant_id, scan_id, "complete")
        scan.baseline_score = baseline_score
        scan.current_score = current_score
        scan.delta_pct = delta_pct
        scan.severity = severity.value
        scan.result = result
        scan.completed_at = utc_now()
        return await self.repos.regression_scans.update(scan)

    async def fail(self, tenant_id: str, scan_id: str, *, error: str) -> RegressionScanModel:
        scan = await self._apply_transition(tenant_id, scan_id, "fail")
        scan.error = error
        scan.completed_at = utc_now()
        return await self.repos.regression_scans.update(scan)

    async def run_scan(self, tenant_id: str, scan_id: str) -> RegressionScanModel:
        await self.start(tenant_id, scan_id)
        scan = await self.get_or_404(tenant_id, scan_id)

        baseline = await self.repos.ai_quality_baselines.get_for_subject(tenant_id, scan.dimension, scan.subject_ref)
        if baseline is None:
            return await self.fail(tenant_id, scan_id, error=f"No baseline recorded for '{scan.dimension}:{scan.subject_ref}'")

        current_score = await self.evaluations.latest_score(tenant_id, scan.dimension, scan.subject_ref)
        if current_score is None:
            return await self.fail(tenant_id, scan_id, error=f"No evaluations recorded for '{scan.dimension}:{scan.subject_ref}'")

        delta_pct, severity = classify_regression(
            baseline.baseline_score, current_score, threshold_pct=self.settings.ai_quality_regression_threshold_pct
        )
        result = {
            "baseline_score": baseline.baseline_score, "current_score": current_score,
            "delta_pct": delta_pct, "severity": severity.value,
        }
        return await self.complete(
            tenant_id, scan_id, baseline_score=baseline.baseline_score, current_score=current_score,
            delta_pct=delta_pct, severity=severity, result=result,
        )

    def assert_no_regression(self, scan: RegressionScanModel) -> None:
        if scan.severity in (RegressionSeverity.MAJOR.value, RegressionSeverity.CRITICAL.value):
            raise RegressionDetectedError(
                f"Regression scan '{scan.id}' detected {scan.severity} drift ({scan.delta_pct:.1f}%) on "
                f"'{scan.dimension}:{scan.subject_ref}'"
            )

    async def list_scans(self, tenant_id: str, *, dimension: str | None = None, limit: int = 100) -> list[RegressionScanModel]:
        return await self.repos.regression_scans.list_for_tenant(tenant_id, dimension=dimension, limit=limit)
