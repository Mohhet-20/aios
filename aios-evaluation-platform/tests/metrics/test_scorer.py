import pytest

from eval_platform.core.exceptions import MetricComputationError, UnknownMetricError
from eval_platform.metrics.inputs import MetricInput
from eval_platform.metrics.registry import METRIC_SPECS


@pytest.mark.asyncio
async def test_sync_definitions_creates_all_20(scorer):
    synced = await scorer.sync_definitions()
    assert len(synced) == len(METRIC_SPECS)


@pytest.mark.asyncio
async def test_sync_definitions_is_idempotent(scorer):
    await scorer.sync_definitions()
    synced_again = await scorer.sync_definitions()
    assert len(synced_again) == len(METRIC_SPECS)


def test_compute_unknown_metric_raises(scorer):
    with pytest.raises(UnknownMetricError):
        scorer.compute("not_real", MetricInput())


def test_compute_many_raises_by_default(scorer):
    with pytest.raises(MetricComputationError):
        scorer.compute_many(["accuracy", "latency"], MetricInput(actual_output="a", expected_output="a"))


def test_compute_many_skip_errors(scorer):
    results = scorer.compute_many(
        ["accuracy", "latency"], MetricInput(actual_output="a", expected_output="a"), skip_errors=True,
    )
    assert results["accuracy"] == 1.0
    assert results["latency"] is None


@pytest.mark.asyncio
async def test_record_result_persists_metric_result(scorer, workspace, repos):
    result = await scorer.record_result(
        workspace.id, "accuracy", subject_type="adhoc", subject_id=None,
        metric_input=MetricInput(actual_output="Paris", expected_output="Paris"),
    )
    assert result.value == 1.0
    persisted = await repos.metric_results.get_or_404(result.id)
    assert persisted.metric_key == "accuracy"
    assert persisted.subject_type == "adhoc"
