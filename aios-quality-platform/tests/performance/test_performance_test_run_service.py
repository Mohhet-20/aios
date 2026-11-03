import pytest

from quality_platform.core.exceptions import InvalidTransitionError, UnsupportedPerformanceTestTypeError
from quality_platform.performance.benchmark_result_service import BenchmarkResultService
from quality_platform.performance.performance_test_run_service import PerformanceTestRunService

pytestmark = pytest.mark.asyncio


async def test_request_run_rejects_unsupported_type(repos):
    svc = PerformanceTestRunService(repos)
    with pytest.raises(UnsupportedPerformanceTestTypeError):
        await svc.request_run("t1", performance_test_type="not-a-type", target_ref="svc:1")


async def test_request_run_defaults_config_duration(repos):
    svc = PerformanceTestRunService(repos)
    run = await svc.request_run("t1", performance_test_type="load", target_ref="svc:1")
    assert run.config["duration_seconds"] == svc.settings.performance_default_duration_seconds


async def test_start_complete_lifecycle(repos):
    svc = PerformanceTestRunService(repos)
    run = await svc.request_run("t1", performance_test_type="stress", target_ref="svc:1")
    assert run.status == "queued"
    started = await svc.start("t1", run.id)
    assert started.status == "running"
    completed = await svc.complete("t1", run.id, result={"ok": True})
    assert completed.status == "completed"
    assert completed.completed_at is not None


async def test_cannot_complete_without_start(repos):
    svc = PerformanceTestRunService(repos)
    run = await svc.request_run("t1", performance_test_type="soak", target_ref="svc:1")
    with pytest.raises(InvalidTransitionError):
        await svc.complete("t1", run.id, result={})


async def test_finish_run_flags_bottleneck_from_recorded_metrics(repos):
    svc = PerformanceTestRunService(repos)
    benchmarks = BenchmarkResultService(repos)
    run = await svc.request_run("t1", performance_test_type="load", target_ref="svc:1")
    await svc.start("t1", run.id)
    await benchmarks.record_result("t1", run.id, metric_type="cpu_utilization", value=95.0, unit="pct")
    await benchmarks.record_result("t1", run.id, metric_type="error_rate", value=1.0, unit="pct")

    finished = await svc.finish_run("t1", run.id)
    assert finished.status == "completed"
    assert "cpu_bound" in finished.result["bottlenecks"]
    assert finished.result["capacity_verdict"] == "at_capacity"


async def test_finish_run_healthy_when_no_bottlenecks(repos):
    svc = PerformanceTestRunService(repos)
    benchmarks = BenchmarkResultService(repos)
    run = await svc.request_run("t1", performance_test_type="load", target_ref="svc:2")
    await svc.start("t1", run.id)
    await benchmarks.record_result("t1", run.id, metric_type="cpu_utilization", value=20.0, unit="pct")

    finished = await svc.finish_run("t1", run.id)
    assert finished.result["capacity_verdict"] == "healthy"
