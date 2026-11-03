from datetime import datetime, timedelta, timezone

import pytest


@pytest.mark.asyncio
async def test_quality_snapshot_averages_scores_in_window(snapshot_service, run_service, ready_evaluation, executor):
    run = await run_service.start_run(ready_evaluation.id, triggered_by="u1")
    await run_service.execute_run(run.id, executor)

    now = datetime.now(timezone.utc)
    snapshot = await snapshot_service.build_quality_snapshot(ready_evaluation.workspace_id, period_start=now - timedelta(hours=1), period_end=now + timedelta(hours=1))
    assert snapshot.data["run_count"] == 1
    assert snapshot.data["avg_overall_score"] == 1.0
    assert snapshot.data["pass_rate"] == 1.0


@pytest.mark.asyncio
async def test_quality_snapshot_excludes_runs_outside_window(snapshot_service, run_service, ready_evaluation, executor):
    run = await run_service.start_run(ready_evaluation.id, triggered_by="u1")
    await run_service.execute_run(run.id, executor)

    now = datetime.now(timezone.utc)
    snapshot = await snapshot_service.build_quality_snapshot(ready_evaluation.workspace_id, period_start=now + timedelta(days=1), period_end=now + timedelta(days=2))
    assert snapshot.data["run_count"] == 0
    assert snapshot.data["avg_overall_score"] is None


@pytest.mark.asyncio
async def test_reliability_and_cost_and_usage_snapshots(snapshot_service, ingestion_service, workspace):
    await ingestion_service.ingest_event(workspace.id, event_type="tool_call", source_platform="tool_platform", status="succeeded", cost=0.5, token_usage={"input_tokens": 10, "output_tokens": 5})
    await ingestion_service.ingest_event(workspace.id, event_type="tool_call", source_platform="tool_platform", status="failed", error_type="TimeoutError", retry_count=1)

    now = datetime.now(timezone.utc)
    period_start, period_end = now - timedelta(hours=1), now + timedelta(hours=1)

    reliability = await snapshot_service.build_reliability_snapshot(workspace.id, period_start=period_start, period_end=period_end)
    assert reliability.data["event_count"] == 2
    assert reliability.data["failure_count"] == 1
    assert reliability.data["failure_rate"] == 0.5

    cost = await snapshot_service.build_cost_snapshot(workspace.id, period_start=period_start, period_end=period_end)
    assert cost.data["total_cost"] == 0.5

    usage = await snapshot_service.build_usage_snapshot(workspace.id, period_start=period_start, period_end=period_end)
    assert usage.data["total_events"] == 2
    assert usage.data["event_count_by_type"] == {"tool_call": 2}
    assert usage.data["input_tokens"] == 10


@pytest.mark.asyncio
async def test_regression_snapshot_requires_ordered_windows(snapshot_service, workspace):
    now = datetime.now(timezone.utc)
    with pytest.raises(Exception):
        await snapshot_service.build_regression_snapshot(
            workspace.id, "eval-1", period_start=now, period_end=now + timedelta(hours=1), previous_period_start=now,
        )


@pytest.mark.asyncio
async def test_regression_snapshot_detects_a_real_drop(snapshot_service, run_service, ready_evaluation, repos, executor):
    now = datetime.now(timezone.utc)

    # A good run (accuracy 1.0), backdated into the "previous" window.
    run1 = await run_service.start_run(ready_evaluation.id, triggered_by="u1")
    await run_service.execute_run(run1.id, executor)
    run1_model = await repos.evaluation_runs.get_or_404(run1.id)
    run1_model.created_at = now - timedelta(hours=3)
    await repos.evaluation_runs.update(run1_model)

    # Republish with a wrong static response so the next run scores 0.0.
    from eval_platform.evaluation_core.version_service import EvaluationVersionService
    vs = EvaluationVersionService(repos)
    draft = await vs.get_or_create_draft(ready_evaluation.id, created_by="u1")
    await vs.update_draft(draft.id, target_config={"type": "prompt", "response_map": {}, "static_response": "wrong"})
    await vs.publish_version(draft.id)

    # A bad run (accuracy 0.0), left at "now" so it falls in the "current" window.
    run2 = await run_service.start_run(ready_evaluation.id, triggered_by="u1")
    await run_service.execute_run(run2.id, executor)

    snapshot = await snapshot_service.build_regression_snapshot(
        ready_evaluation.workspace_id, ready_evaluation.id, period_start=now - timedelta(hours=1),
        period_end=now + timedelta(hours=1), previous_period_start=now - timedelta(hours=4),
    )
    assert snapshot.data["current_avg_score"] == 0.0
    assert snapshot.data["previous_avg_score"] == 1.0
    assert snapshot.data["delta"] == -1.0
    assert snapshot.data["regressed"] is True
