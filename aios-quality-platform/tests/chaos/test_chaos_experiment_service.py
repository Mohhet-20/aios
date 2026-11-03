import pytest

from quality_platform.chaos.chaos_experiment_service import ChaosExperimentService
from quality_platform.core.exceptions import (
    BlastRadiusExceededError,
    InvalidTransitionError,
    UnsupportedFailureTypeError,
)

pytestmark = pytest.mark.asyncio


async def test_request_experiment_rejects_unsupported_failure_type(repos):
    svc = ChaosExperimentService(repos)
    with pytest.raises(UnsupportedFailureTypeError):
        await svc.request_experiment("t1", failure_type="not-a-type", target_ref="svc:1", blast_radius_pct=5.0)


async def test_request_experiment_rejects_blast_radius_over_cap(repos):
    svc = ChaosExperimentService(repos)
    with pytest.raises(BlastRadiusExceededError):
        await svc.request_experiment("t1", failure_type="node_failure", target_ref="svc:1", blast_radius_pct=50.0)


async def test_request_experiment_accepts_within_cap(repos):
    svc = ChaosExperimentService(repos)
    exp = await svc.request_experiment("t1", failure_type="node_failure", target_ref="svc:1", blast_radius_pct=10.0)
    assert exp.status == "queued"
    assert exp.blast_radius_pct == 10.0


async def test_start_finish_experiment_recovered(repos):
    svc = ChaosExperimentService(repos)
    exp = await svc.request_experiment("t1", failure_type="network_latency", target_ref="svc:1", blast_radius_pct=15.0)
    await svc.start("t1", exp.id)
    finished = await svc.finish_experiment("t1", exp.id, recovered=True, recovery_time_seconds=4.2)
    assert finished.status == "completed"
    assert finished.recovered is True
    assert finished.recovery_time_seconds == 4.2
    assert finished.completed_at is not None


async def test_finish_experiment_not_recovered(repos):
    svc = ChaosExperimentService(repos)
    exp = await svc.request_experiment("t1", failure_type="cache_failure", target_ref="svc:2", blast_radius_pct=10.0)
    await svc.start("t1", exp.id)
    finished = await svc.finish_experiment("t1", exp.id, recovered=False)
    assert finished.recovered is False
    assert finished.recovery_time_seconds is None


async def test_cannot_complete_without_start(repos):
    svc = ChaosExperimentService(repos)
    exp = await svc.request_experiment("t1", failure_type="worker_failure", target_ref="svc:3", blast_radius_pct=5.0)
    with pytest.raises(InvalidTransitionError):
        await svc.complete("t1", exp.id, result={}, recovered=True, recovery_time_seconds=1.0)


async def test_fail_experiment(repos):
    svc = ChaosExperimentService(repos)
    exp = await svc.request_experiment("t1", failure_type="queue_failure", target_ref="svc:4", blast_radius_pct=5.0)
    await svc.start("t1", exp.id)
    failed = await svc.fail("t1", exp.id, error="injection tooling crashed")
    assert failed.status == "failed"
    assert failed.error == "injection tooling crashed"


async def test_list_experiments_filters_by_failure_type(repos):
    svc = ChaosExperimentService(repos)
    await svc.request_experiment("t1", failure_type="storage_failure", target_ref="svc:5", blast_radius_pct=5.0)
    await svc.request_experiment("t1", failure_type="gpu_failure", target_ref="svc:6", blast_radius_pct=5.0)
    storage_only = await svc.list_experiments("t1", failure_type="storage_failure")
    assert len(storage_only) == 1
    assert storage_only[0].failure_type == "storage_failure"
