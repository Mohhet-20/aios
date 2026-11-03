"""Tests for experiment tracking: experiment CRUD, run lifecycle,
multi-step metric logging, once-per-key parameter logging, run
comparison, and stale-metric pruning."""
from __future__ import annotations

import pytest

from infra_platform.config.settings import Settings
from infra_platform.core.exceptions import ExperimentError, NotFoundError, RunAlreadyFinishedError, RunNotFoundError
from infra_platform.experiments.experiment_service import ExperimentRunService, ExperimentService

TENANT = "tenant-experiments"


@pytest.mark.asyncio
async def test_create_experiment_rejects_duplicate_name(repos):
    service = ExperimentService(repos)
    await service.create_experiment(TENANT, name="fraud-detection")
    with pytest.raises(ExperimentError):
        await service.create_experiment(TENANT, name="fraud-detection")


@pytest.mark.asyncio
async def test_run_lifecycle_complete(repos):
    exp_service = ExperimentService(repos)
    run_service = ExperimentRunService(repos)
    experiment = await exp_service.create_experiment(TENANT, name="lr-sweep")

    run = await run_service.start_run(TENANT, experiment.id, run_name="trial-1")
    assert run.status == "running"

    run = await run_service.complete_run(TENANT, run.id)
    assert run.status == "completed"
    assert run.finished_at is not None

    from infra_platform.core.exceptions import InvalidTransitionError
    with pytest.raises(InvalidTransitionError):
        await run_service.fail_run(TENANT, run.id)


@pytest.mark.asyncio
async def test_run_lifecycle_fail_and_kill(repos):
    exp_service = ExperimentService(repos)
    run_service = ExperimentRunService(repos)
    experiment = await exp_service.create_experiment(TENANT, name="fail-sweep")

    run_a = await run_service.start_run(TENANT, experiment.id)
    run_a = await run_service.fail_run(TENANT, run_a.id)
    assert run_a.status == "failed"

    run_b = await run_service.start_run(TENANT, experiment.id)
    run_b = await run_service.kill_run(TENANT, run_b.id)
    assert run_b.status == "killed"


@pytest.mark.asyncio
async def test_metric_logging_multi_step_and_blocked_after_finish(repos):
    exp_service = ExperimentService(repos)
    run_service = ExperimentRunService(repos)
    experiment = await exp_service.create_experiment(TENANT, name="metric-exp")
    run = await run_service.start_run(TENANT, experiment.id)

    await run_service.log_metric(TENANT, run.id, key="loss", value=0.9, step=0)
    await run_service.log_metric(TENANT, run.id, key="loss", value=0.5, step=1)
    await run_service.log_metric(TENANT, run.id, key="loss", value=0.2, step=2)

    history = await run_service.get_metrics(TENANT, run.id, key="loss")
    assert [m.value for m in history] == [0.9, 0.5, 0.2]

    await run_service.complete_run(TENANT, run.id)
    with pytest.raises(RunAlreadyFinishedError):
        await run_service.log_metric(TENANT, run.id, key="loss", value=0.1, step=3)


@pytest.mark.asyncio
async def test_param_logged_once_per_key(repos):
    exp_service = ExperimentService(repos)
    run_service = ExperimentRunService(repos)
    experiment = await exp_service.create_experiment(TENANT, name="param-exp")
    run = await run_service.start_run(TENANT, experiment.id)

    await run_service.log_param(TENANT, run.id, key="learning_rate", value="0.001")
    with pytest.raises(ExperimentError):
        await run_service.log_param(TENANT, run.id, key="learning_rate", value="0.002")

    params = await run_service.get_params(TENANT, run.id)
    assert len(params) == 1
    assert params[0].value == "0.001"


@pytest.mark.asyncio
async def test_compare_runs_across_metric_key(repos):
    exp_service = ExperimentService(repos)
    run_service = ExperimentRunService(repos)
    experiment = await exp_service.create_experiment(TENANT, name="compare-exp")

    run_a = await run_service.start_run(TENANT, experiment.id, run_name="a")
    run_b = await run_service.start_run(TENANT, experiment.id, run_name="b")
    run_c = await run_service.start_run(TENANT, experiment.id, run_name="c")

    await run_service.log_metric(TENANT, run_a.id, key="accuracy", value=0.91)
    await run_service.log_metric(TENANT, run_b.id, key="accuracy", value=0.5)
    await run_service.log_metric(TENANT, run_b.id, key="accuracy", value=0.95, step=1)
    # run_c never logs accuracy

    comparison = await run_service.compare_runs(TENANT, [run_a.id, run_b.id, run_c.id], metric_key="accuracy")
    assert comparison == {run_a.id: 0.91, run_b.id: 0.95, run_c.id: None}


@pytest.mark.asyncio
async def test_prune_stale_metrics(repos):
    exp_service = ExperimentService(repos)
    run_service = ExperimentRunService(repos, settings=Settings(experiment_metric_retention_days=0))
    experiment = await exp_service.create_experiment(TENANT, name="prune-exp")
    run = await run_service.start_run(TENANT, experiment.id)

    await run_service.log_metric(TENANT, run.id, key="loss", value=1.0)
    import asyncio
    await asyncio.sleep(1.1)

    pruned = await run_service.prune_stale_metrics(TENANT, run.id)
    assert pruned == 1
    remaining = await run_service.get_metrics(TENANT, run.id)
    assert remaining == []


@pytest.mark.asyncio
async def test_run_and_experiment_not_found(repos):
    run_service = ExperimentRunService(repos)
    with pytest.raises(NotFoundError):
        await run_service.start_run(TENANT, "no-such-experiment")
    with pytest.raises(RunNotFoundError):
        await run_service.complete_run(TENANT, "no-such-run")
