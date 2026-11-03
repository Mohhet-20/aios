import pytest

from eval_platform.core.exceptions import ValidationError


@pytest.mark.asyncio
async def test_start_run_requires_published_evaluation(run_service, evaluation_service, workspace):
    draft_only = await evaluation_service.create_evaluation(workspace.id, name="Unpublished", owner_id="u1", category="prompt", organization_id="org-1")
    with pytest.raises(ValidationError):
        await run_service.start_run(draft_only.id)


@pytest.mark.asyncio
async def test_execute_run_scores_all_items_and_succeeds(run_service, ready_evaluation, executor):
    run = await run_service.start_run(ready_evaluation.id, triggered_by="u1")
    completed = await run_service.execute_run(run.id, executor)

    assert completed.status == "succeeded"
    assert completed.item_count == 2
    assert completed.passed_count == 2
    assert completed.overall_score == 1.0
    assert completed.metric_summary == {"accuracy": 1.0}
    assert completed.started_at is not None
    assert completed.completed_at is not None


@pytest.mark.asyncio
async def test_execute_run_persists_per_item_results(run_service, ready_evaluation, executor):
    run = await run_service.start_run(ready_evaluation.id, triggered_by="u1")
    await run_service.execute_run(run.id, executor)

    results = await run_service.list_item_results(run.id)
    assert len(results) == 2
    assert all(r.passed for r in results)
    assert all(r.metric_results.get("accuracy") == 1.0 for r in results)


@pytest.mark.asyncio
async def test_execute_run_with_unconfigured_target_marks_item_failed_not_run(run_service, evaluation_service, evaluation_version_service, dataset_service, dataset_version_service, workspace, executor):
    dataset = await dataset_service.create_dataset(workspace.id, name="D", owner_id="u1", dataset_type="golden", organization_id="org-1")
    draft = await dataset_version_service.get_or_create_draft(dataset.id, created_by="u1")
    await dataset_version_service.add_items(draft.id, [{"input_data": {"q": "1"}, "expected_output": "1"}])
    await dataset_version_service.publish_version(draft.id)

    evaluation = await evaluation_service.create_evaluation(workspace.id, name="Unconfigured", owner_id="u1", category="prompt", organization_id="org-1")
    eval_draft = await evaluation_version_service.get_or_create_draft(evaluation.id, created_by="u1")
    await evaluation_version_service.update_draft(
        eval_draft.id, dataset_id=dataset.id, metric_keys=["accuracy"], target_config={"type": "prompt"},
    )
    await evaluation_version_service.publish_version(eval_draft.id)
    evaluation = await evaluation_service.get_evaluation(evaluation.id)

    run = await run_service.start_run(evaluation.id, triggered_by="u1")
    completed = await run_service.execute_run(run.id, executor)

    assert completed.status == "succeeded"
    assert completed.passed_count == 0
    results = await run_service.list_item_results(run.id)
    assert results[0].passed is False
    assert "no configured response" in results[0].error_message


@pytest.mark.asyncio
async def test_execute_run_fails_when_dataset_not_bound(run_service, evaluation_service, evaluation_version_service, workspace, executor):
    evaluation = await evaluation_service.create_evaluation(workspace.id, name="NoDataset", owner_id="u1", category="prompt", organization_id="org-1")
    eval_draft = await evaluation_version_service.get_or_create_draft(evaluation.id, created_by="u1")
    await evaluation_version_service.update_draft(eval_draft.id, metric_keys=["accuracy"], target_config={"type": "prompt"})
    await evaluation_version_service.publish_version(eval_draft.id)
    evaluation = await evaluation_service.get_evaluation(evaluation.id)

    run = await run_service.start_run(evaluation.id, triggered_by="u1")
    with pytest.raises(Exception):
        await run_service.execute_run(run.id, executor)

    refreshed = await run_service.get_run(run.id)
    assert refreshed.status == "failed"
    assert refreshed.error_message
