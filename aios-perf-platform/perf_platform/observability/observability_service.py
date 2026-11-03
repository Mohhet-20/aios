"""Latency/throughput tracking and benchmark-run orchestration. The
percentile/throughput math lives in metrics_rules.py (pure, unit-
tested in isolation); these services are the thin DB-backed shell
around it, plus the guarded `BenchmarkRun` lifecycle."""
from __future__ import annotations


from perf_platform.config.settings import get_settings
from perf_platform.core.exceptions import BenchmarkNotFoundError
from perf_platform.domain.entities import BenchmarkRun
from perf_platform.domain.enums import JobStatus
from perf_platform.models.observability import BenchmarkRunModel, LatencySampleModel, ThroughputSampleModel
from perf_platform.observability.metrics_rules import improvement_pct, mean, percentile, throughput_per_second
from perf_platform.repositories.registry import RepositoryRegistry
from perf_platform.clock import utc_now


class LatencyTrackingService:
    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos
        self.settings = get_settings()

    async def record(self, tenant_id: str, operation: str, duration_ms: float) -> LatencySampleModel:
        sample = await self.repos.latency_samples.add(
            LatencySampleModel(tenant_id=tenant_id, operation=operation, duration_ms=duration_ms, recorded_at=utc_now())
        )
        await self.repos.session.commit()
        return sample

    async def percentiles(self, tenant_id: str, operation: str) -> dict[str, float]:
        samples = await self.repos.latency_samples.list_for_operation(tenant_id, operation)
        durations = [s.duration_ms for s in samples]
        result = {f"p{int(p)}": percentile(durations, p) for p in self.settings.latency_percentiles}
        result["mean"] = mean(durations)
        result["sample_count"] = float(len(durations))
        return result

    async def slo_status(self, tenant_id: str, operation: str) -> dict[str, object]:
        stats = await self.percentiles(tenant_id, operation)
        p95 = stats.get("p95", 0.0)
        p99 = stats.get("p99", 0.0)
        return {
            "p95_ms": p95,
            "p99_ms": p99,
            "p95_within_slo": p95 <= self.settings.slo_p95_latency_ms,
            "p99_within_slo": p99 <= self.settings.slo_p99_latency_ms,
        }


class ThroughputTrackingService:
    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos

    async def record(self, tenant_id: str, operation: str, *, request_count: int, window_seconds: float) -> ThroughputSampleModel:
        sample = await self.repos.throughput_samples.add(
            ThroughputSampleModel(
                tenant_id=tenant_id, operation=operation, request_count=request_count, window_seconds=window_seconds,
                recorded_at=utc_now(),
            )
        )
        await self.repos.session.commit()
        return sample

    async def current_rate(self, tenant_id: str, operation: str) -> float:
        samples = await self.repos.throughput_samples.list_for_operation(tenant_id, operation, limit=1)
        if not samples:
            return 0.0
        latest = samples[0]
        return throughput_per_second(request_count=latest.request_count, window_seconds=latest.window_seconds)


class BenchmarkService:
    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos

    async def get_or_404(self, tenant_id: str, run_id: str) -> BenchmarkRunModel:
        run = await self.repos.benchmark_runs.get_or_404(run_id)
        if run.tenant_id != tenant_id:
            raise BenchmarkNotFoundError(f"BenchmarkRun '{run_id}' not found for tenant '{tenant_id}'")
        return run

    async def start(self, tenant_id: str, *, name: str, target_ref: str | None = None) -> BenchmarkRunModel:
        run = await self.repos.benchmark_runs.add(BenchmarkRunModel(tenant_id=tenant_id, name=name, target_ref=target_ref))
        await self.repos.session.commit()
        entity = BenchmarkRun(id=run.id, status=JobStatus(run.status))
        entity.start()
        run.status = entity.status.value
        await self.repos.session.commit()
        return run

    async def complete(self, tenant_id: str, run_id: str, *, baseline_ms: float, optimized_ms: float) -> BenchmarkRunModel:
        run = await self.get_or_404(tenant_id, run_id)
        entity = BenchmarkRun(id=run.id, status=JobStatus(run.status))
        entity.complete()
        run.status = entity.status.value
        run.baseline_ms = baseline_ms
        run.optimized_ms = optimized_ms
        run.improvement_pct = improvement_pct(baseline_ms=baseline_ms, optimized_ms=optimized_ms)
        await self.repos.session.commit()
        return run

    async def fail(self, tenant_id: str, run_id: str) -> BenchmarkRunModel:
        run = await self.get_or_404(tenant_id, run_id)
        entity = BenchmarkRun(id=run.id, status=JobStatus(run.status))
        entity.fail()
        run.status = entity.status.value
        await self.repos.session.commit()
        return run

    async def list_for_tenant(self, tenant_id: str, *, status: str | None = None) -> list[BenchmarkRunModel]:
        return await self.repos.benchmark_runs.list_for_tenant(tenant_id, status=status)
