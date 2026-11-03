from datetime import datetime, timedelta, timezone

import pytest

from eval_platform.models.run import EvaluationItemResultModel


@pytest.mark.asyncio
async def test_cluster_run_failures_groups_by_error_message(improvement_loop, run_service, ready_evaluation, repos):
    run = await run_service.start_run(ready_evaluation.id, triggered_by="u1")
    for _ in range(2):
        await repos.evaluation_item_results.add(EvaluationItemResultModel(
            run_id=run.id, input_data={}, expected_output={}, actual_output={}, metric_results={}, passed=False,
            error_message="timeout calling backend",
        ))
    await repos.evaluation_item_results.add(EvaluationItemResultModel(
        run_id=run.id, input_data={}, expected_output={}, actual_output={}, metric_results={"accuracy": 1.0}, passed=True,
    ))

    clusters = await improvement_loop.cluster_run_failures(run.id)
    assert clusters == {"timeout calling backend": [
        c.id for c in await repos.evaluation_item_results.list_for_run(run.id) if not c.passed
    ]}


@pytest.mark.asyncio
async def test_cluster_run_failures_falls_back_to_lowest_metric(improvement_loop, run_service, ready_evaluation, repos):
    run = await run_service.start_run(ready_evaluation.id, triggered_by="u1")
    await repos.evaluation_item_results.add(EvaluationItemResultModel(
        run_id=run.id, input_data={}, expected_output={}, actual_output={}, metric_results={"accuracy": 0.1, "recall": 0.9}, passed=False,
    ))

    clusters = await improvement_loop.cluster_run_failures(run.id)
    assert "low 'accuracy' score" in clusters


@pytest.mark.asyncio
async def test_detect_score_regression_needs_enough_runs(improvement_loop, run_service, ready_evaluation, executor):
    run = await run_service.start_run(ready_evaluation.id, triggered_by="u1")
    await run_service.execute_run(run.id, executor)
    result = await improvement_loop.detect_score_regression(ready_evaluation.id, window=1)
    assert result is None  # only 1 scored run, needs 2*window=2


@pytest.mark.asyncio
async def test_detect_score_regression_finds_a_real_drop(improvement_loop, run_service, ready_evaluation, repos, executor):
    now = datetime.now(timezone.utc)

    good_run = await run_service.start_run(ready_evaluation.id, triggered_by="u1")
    await run_service.execute_run(good_run.id, executor)
    good_model = await repos.evaluation_runs.get_or_404(good_run.id)
    good_model.created_at = now - timedelta(hours=2)
    await repos.evaluation_runs.update(good_model)

    from eval_platform.evaluation_core.version_service import EvaluationVersionService
    vs = EvaluationVersionService(repos)
    draft = await vs.get_or_create_draft(ready_evaluation.id, created_by="u1")
    await vs.update_draft(draft.id, target_config={"type": "prompt", "response_map": {}, "static_response": "wrong"})
    await vs.publish_version(draft.id)

    bad_run = await run_service.start_run(ready_evaluation.id, triggered_by="u1")
    await run_service.execute_run(bad_run.id, executor)

    regression = await improvement_loop.detect_score_regression(ready_evaluation.id, window=1)
    assert regression is not None
    assert regression["recent_avg_score"] == 0.0
    assert regression["prior_avg_score"] == 1.0
    assert regression["delta"] == -1.0


@pytest.mark.asyncio
async def test_generate_recommendations_creates_regression_and_cluster_recommendations(improvement_loop, run_service, ready_evaluation, repos, executor):
    now = datetime.now(timezone.utc)
    good_run = await run_service.start_run(ready_evaluation.id, triggered_by="u1")
    await run_service.execute_run(good_run.id, executor)
    good_model = await repos.evaluation_runs.get_or_404(good_run.id)
    good_model.created_at = now - timedelta(hours=2)
    await repos.evaluation_runs.update(good_model)

    from eval_platform.evaluation_core.version_service import EvaluationVersionService
    vs = EvaluationVersionService(repos)
    draft = await vs.get_or_create_draft(ready_evaluation.id, created_by="u1")
    await vs.update_draft(draft.id, target_config={"type": "prompt", "response_map": {}, "static_response": "wrong"})
    await vs.publish_version(draft.id)

    bad_run = await run_service.start_run(ready_evaluation.id, triggered_by="u1")
    await run_service.execute_run(bad_run.id, executor)
    for _ in range(2):
        await repos.evaluation_item_results.add(EvaluationItemResultModel(
            run_id=bad_run.id, input_data={}, expected_output={}, actual_output={}, metric_results={}, passed=False,
            error_message="model returned empty output",
        ))

    recs = await improvement_loop.generate_recommendations(ready_evaluation.workspace_id, ready_evaluation.id, latest_run_id=bad_run.id, regression_window=1)
    categories = {r.category for r in recs}
    assert "reliability" in categories
    assert "prompt_improvement" in categories
