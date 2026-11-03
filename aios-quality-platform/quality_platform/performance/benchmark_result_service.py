"""Benchmark result recording against a performance test run — the
per-metric time series `bottleneck_rules.analyze_bottlenecks` reads
its latest snapshot from."""
from __future__ import annotations

from quality_platform.models.performance import BenchmarkResultModel
from quality_platform.repositories.registry import RepositoryRegistry


class BenchmarkResultService:
    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos

    async def record_result(
        self, tenant_id: str, performance_test_run_id: str, *, metric_type: str, value: float, unit: str = "ms"
    ) -> BenchmarkResultModel:
        result = BenchmarkResultModel(
            tenant_id=tenant_id, performance_test_run_id=performance_test_run_id,
            metric_type=metric_type, value=value, unit=unit,
        )
        return await self.repos.benchmark_results.add(result)

    async def list_for_run(self, tenant_id: str, performance_test_run_id: str) -> list[BenchmarkResultModel]:
        return await self.repos.benchmark_results.list_for_run(tenant_id, performance_test_run_id)

    async def latest_metrics(self, tenant_id: str, performance_test_run_id: str) -> dict[str, float]:
        """Collapses a run's benchmark rows into one value per metric
        type (last-write-wins by insertion order), the shape
        `bottleneck_rules.analyze_bottlenecks` expects."""
        results = await self.list_for_run(tenant_id, performance_test_run_id)
        metrics: dict[str, float] = {}
        for r in results:
            metrics[r.metric_type] = r.value
        return metrics
