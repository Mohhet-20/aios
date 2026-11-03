import pytest

from eval_platform.core.exceptions import BenchmarkError
from eval_platform.datasets.version_service import DatasetVersionService


async def _response_map(repos, dataset):
    version_service = DatasetVersionService(repos)
    items = await version_service.list_items(dataset.current_version_id)
    return {item.id: item.expected_output for item in items}, items


@pytest.mark.asyncio
async def test_start_run_requires_at_least_one_candidate(run_service, ready_benchmark):
    with pytest.raises(BenchmarkError):
        await run_service.start_run(ready_benchmark.id, [])


@pytest.mark.asyncio
async def test_start_run_requires_unique_nonempty_labels(run_service, ready_benchmark):
    with pytest.raises(BenchmarkError):
        await run_service.start_run(ready_benchmark.id, [{"label": "a"}, {"label": "a"}])
    with pytest.raises(BenchmarkError):
        await run_service.start_run(ready_benchmark.id, [{"label": ""}])


@pytest.mark.asyncio
async def test_execute_run_compares_two_candidates(run_service, ready_benchmark, ready_dataset, repos, executor):
    response_map, items = await _response_map(repos, ready_dataset)
    perfect_map = dict(response_map)
    wrong_map = {item.id: "wrong answer" for item in items}

    run = await run_service.start_run(ready_benchmark.id, [
        {"label": "candidate-perfect", "type": "model", "response_map": perfect_map},
        {"label": "candidate-wrong", "type": "model", "response_map": wrong_map},
    ], triggered_by="u1")

    completed = await run_service.execute_run(run.id, executor)
    assert completed.status == "succeeded"

    results = await run_service.list_candidate_results(run.id)
    assert len(results) == 2

    board = await run_service.leaderboard(run.id)
    assert board[0].candidate_label == "candidate-perfect"
    assert board[0].aggregate_score == 1.0
    assert board[1].candidate_label == "candidate-wrong"
    assert board[1].aggregate_score == 0.0
    assert board[0].item_count == 2
    assert board[0].failure_count == 0


@pytest.mark.asyncio
async def test_execute_run_counts_unconfigured_candidate_as_failures(run_service, ready_benchmark, executor):
    run = await run_service.start_run(ready_benchmark.id, [{"label": "unconfigured", "type": "model"}], triggered_by="u1")
    completed = await run_service.execute_run(run.id, executor)
    assert completed.status == "succeeded"

    results = await run_service.list_candidate_results(run.id)
    assert results[0].failure_count == 2
    assert results[0].aggregate_score is None


@pytest.mark.asyncio
async def test_execute_run_fails_when_dataset_not_bound(run_service, benchmark_service, workspace, executor):
    benchmark = await benchmark_service.create_benchmark(
        workspace.id, name="No Dataset", owner_id="u1", benchmark_type="model", mode="single", organization_id="org-1",
    )
    run = await run_service.start_run(benchmark.id, [{"label": "a"}], triggered_by="u1")
    with pytest.raises(Exception):
        await run_service.execute_run(run.id, executor)

    refreshed = await run_service.get_run(run.id)
    assert refreshed.status == "failed"
