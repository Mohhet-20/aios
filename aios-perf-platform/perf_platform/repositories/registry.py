"""RepositoryRegistry: per-request unit-of-work that lazily
instantiates and memoizes one repository per model, all sharing the
same AsyncSession — identical pattern to every prior AIOS platform."""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from perf_platform.repositories.cache_repository import CacheEntryRepository, CacheStatRepository
from perf_platform.repositories.cost_repository import BudgetRepository, CostAlertRepository, CostRecordRepository
from perf_platform.repositories.observability_repository import (
    BenchmarkRunRepository,
    LatencySampleRepository,
    ThroughputSampleRepository,
)
from perf_platform.repositories.optimization_repository import RecommendationRepository
from perf_platform.repositories.routing_repository import RoutingDecisionRepository, RoutingPolicyRepository
from perf_platform.repositories.scalability_repository import GpuPoolRepository


class RepositoryRegistry:
    def __init__(self, session: AsyncSession):
        self.session = session
        self._repos: dict[str, object] = {}

    def _get(self, key: str, cls: type):
        if key not in self._repos:
            self._repos[key] = cls(self.session)
        return self._repos[key]

    # -- cache platform --
    @property
    def cache_entries(self) -> CacheEntryRepository:
        return self._get("cache_entries", CacheEntryRepository)

    @property
    def cache_stats(self) -> CacheStatRepository:
        return self._get("cache_stats", CacheStatRepository)

    # -- model routing / LLM cost intelligence --
    @property
    def routing_policies(self) -> RoutingPolicyRepository:
        return self._get("routing_policies", RoutingPolicyRepository)

    @property
    def routing_decisions(self) -> RoutingDecisionRepository:
        return self._get("routing_decisions", RoutingDecisionRepository)

    # -- cost intelligence engine --
    @property
    def cost_records(self) -> CostRecordRepository:
        return self._get("cost_records", CostRecordRepository)

    @property
    def budgets(self) -> BudgetRepository:
        return self._get("budgets", BudgetRepository)

    @property
    def cost_alerts(self) -> CostAlertRepository:
        return self._get("cost_alerts", CostAlertRepository)

    # -- auto-optimization engine --
    @property
    def recommendations(self) -> RecommendationRepository:
        return self._get("recommendations", RecommendationRepository)

    # -- observability & benchmarking --
    @property
    def latency_samples(self) -> LatencySampleRepository:
        return self._get("latency_samples", LatencySampleRepository)

    @property
    def throughput_samples(self) -> ThroughputSampleRepository:
        return self._get("throughput_samples", ThroughputSampleRepository)

    @property
    def benchmark_runs(self) -> BenchmarkRunRepository:
        return self._get("benchmark_runs", BenchmarkRunRepository)

    # -- GPU / scalability --
    @property
    def gpu_pools(self) -> GpuPoolRepository:
        return self._get("gpu_pools", GpuPoolRepository)
