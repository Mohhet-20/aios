"""Performance test run job lifecycle: request_run() enqueues a run
against one of the six performance test types, start()/complete()/fail()
drive the guarded queued -> running -> completed/failed transitions on
the domain-level `PerformanceTestRun` entity, and finish_run() is the
convenience orchestrator that pulls the run's recorded benchmark
results, runs bottleneck/capacity analysis over them, and completes
the run with that analysis attached."""
from __future__ import annotations


from quality_platform.config.settings import get_settings
from quality_platform.core.exceptions import InvalidTransitionError, PerformanceTestRunNotFoundError, UnsupportedPerformanceTestTypeError
from quality_platform.domain.entities import PerformanceTestRun
from quality_platform.domain.enums import JobStatus
from quality_platform.models.performance import PerformanceTestRunModel
from quality_platform.performance.benchmark_result_service import BenchmarkResultService
from quality_platform.performance.bottleneck_rules import analyze_bottlenecks, capacity_verdict
from quality_platform.repositories.registry import RepositoryRegistry
from quality_platform.clock import utc_now


class PerformanceTestRunService:
    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos
        self.settings = get_settings()
        self.benchmarks = BenchmarkResultService(repos)

    async def get_or_404(self, tenant_id: str, run_id: str) -> PerformanceTestRunModel:
        run = await self.repos.performance_test_runs.get_or_404(run_id)
        if run.tenant_id != tenant_id:
            raise PerformanceTestRunNotFoundError(f"Performance test run '{run_id}' not found for tenant '{tenant_id}'")
        return run

    async def request_run(
        self, tenant_id: str, *, performance_test_type: str, target_ref: str, config: dict | None = None
    ) -> PerformanceTestRunModel:
        if performance_test_type not in self.settings.performance_test_types:
            raise UnsupportedPerformanceTestTypeError(f"Unsupported performance test type '{performance_test_type}'")
        run = PerformanceTestRunModel(
            tenant_id=tenant_id, performance_test_type=performance_test_type, target_ref=target_ref,
            status=JobStatus.QUEUED.value, config=config or {"duration_seconds": self.settings.performance_default_duration_seconds},
        )
        return await self.repos.performance_test_runs.add(run)

    async def _apply_transition(self, tenant_id: str, run_id: str, transition_name: str) -> PerformanceTestRunModel:
        run = await self.get_or_404(tenant_id, run_id)
        entity = PerformanceTestRun(id=run.id, status=JobStatus(run.status))
        try:
            getattr(entity, transition_name)()
        except InvalidTransitionError:
            raise
        run.status = entity.status.value
        return run

    async def start(self, tenant_id: str, run_id: str) -> PerformanceTestRunModel:
        run = await self._apply_transition(tenant_id, run_id, "start")
        return await self.repos.performance_test_runs.update(run)

    async def complete(self, tenant_id: str, run_id: str, *, result: dict) -> PerformanceTestRunModel:
        run = await self._apply_transition(tenant_id, run_id, "complete")
        run.result = result
        run.completed_at = utc_now()
        return await self.repos.performance_test_runs.update(run)

    async def fail(self, tenant_id: str, run_id: str, *, error: str) -> PerformanceTestRunModel:
        run = await self._apply_transition(tenant_id, run_id, "fail")
        run.error = error
        run.completed_at = utc_now()
        return await self.repos.performance_test_runs.update(run)

    async def finish_run(self, tenant_id: str, run_id: str) -> PerformanceTestRunModel:
        metrics = await self.benchmarks.latest_metrics(tenant_id, run_id)
        bottlenecks = analyze_bottlenecks(metrics)
        result = {"metrics": metrics, "bottlenecks": bottlenecks, "capacity_verdict": capacity_verdict(bottlenecks)}
        return await self.complete(tenant_id, run_id, result=result)

    async def list_runs(self, tenant_id: str, *, performance_test_type: str | None = None, limit: int = 100) -> list[PerformanceTestRunModel]:
        return await self.repos.performance_test_runs.list_for_tenant(tenant_id, performance_test_type=performance_test_type, limit=limit)
