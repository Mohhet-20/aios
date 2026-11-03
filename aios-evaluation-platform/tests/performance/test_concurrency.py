"""Real concurrency/stress tests — genuinely independent sessions racing
against the same SQLite-file-backed database, not the single rollback-
isolated `repos` fixture every other test file uses. This is the same
kind of test that caught the Tool Platform's governance/session-lock
regression in Phase 9: a bug only shows up under real parallel writers,
never under sequential unit tests."""
from __future__ import annotations

import asyncio

import pytest

from eval_platform.benchmarking.benchmark_service import BenchmarkService
from eval_platform.database.session import session_scope
from eval_platform.datasets.dataset_service import DatasetService
from eval_platform.datasets.version_service import DatasetVersionService
from eval_platform.evaluation_core.evaluation_service import EvaluationService
from eval_platform.evaluation_core.version_service import EvaluationVersionService
from eval_platform.execution.evaluation_run_service import EvaluationRunService
from eval_platform.execution.executor import ReferenceTargetExecutor
from eval_platform.models.workspace import WorkspaceModel
from eval_platform.repositories.registry import RepositoryRegistry


async def _setup_ready_evaluation(*, name_suffix: str) -> tuple[str, str]:
    """Creates a fully published evaluation + 1-item dataset, each step
    committed in its own session — returns (workspace_id, evaluation_id)."""
    async for session in session_scope():
        repos = RepositoryRegistry(session)
        workspace = await repos.workspaces.add(WorkspaceModel(
            name=f"Perf Co {name_suffix}", organization_id="org-1", slug=f"perf-co-{name_suffix}",
        ))
        workspace_id = workspace.id

    async for session in session_scope():
        repos = RepositoryRegistry(session)
        dataset_service = DatasetService(repos)
        dataset_version_service = DatasetVersionService(repos)
        dataset = await dataset_service.create_dataset(workspace_id, name=f"Set {name_suffix}", owner_id="u1", dataset_type="golden", organization_id="org-1")
        draft = await dataset_version_service.get_or_create_draft(dataset.id, created_by="u1")
        await dataset_version_service.add_items(draft.id, [{"input_data": {"q": "1+1"}, "expected_output": "2"}])
        published = await dataset_version_service.publish_version(draft.id)
        items = await dataset_version_service.list_items(published.id)
        item_id = items[0].id
        dataset_id = dataset.id

    async for session in session_scope():
        repos = RepositoryRegistry(session)
        evaluation_service = EvaluationService(repos)
        evaluation_version_service = EvaluationVersionService(repos)
        evaluation = await evaluation_service.create_evaluation(workspace_id, name=f"Eval {name_suffix}", owner_id="u1", category="prompt", organization_id="org-1")
        eval_draft = await evaluation_version_service.get_or_create_draft(evaluation.id, created_by="u1")
        await evaluation_version_service.update_draft(
            eval_draft.id, dataset_id=dataset_id, metric_keys=["accuracy"], pass_threshold=1.0,
            target_config={"type": "prompt", "response_map": {item_id: "2"}},
        )
        await evaluation_version_service.publish_version(eval_draft.id)
        evaluation_id = evaluation.id

    return workspace_id, evaluation_id


@pytest.mark.asyncio
async def test_concurrent_independent_evaluation_runs_all_succeed():
    """N fully independent evaluations, each started and executed
    through its own session, all in flight at once against the same
    database file."""
    n = 8
    setups = await asyncio.gather(*[_setup_ready_evaluation(name_suffix=str(i)) for i in range(n)])

    async def run_one(workspace_id: str, evaluation_id: str) -> str:
        async for session in session_scope():
            repos = RepositoryRegistry(session)
            run_service = EvaluationRunService(repos)
            run = await run_service.start_run(evaluation_id, triggered_by="u1")
            run_id = run.id
        async for session in session_scope():
            repos = RepositoryRegistry(session)
            run_service = EvaluationRunService(repos)
            completed = await run_service.execute_run(run_id, ReferenceTargetExecutor())
            return completed.status

    statuses = await asyncio.gather(*[run_one(ws, ev) for ws, ev in setups])
    assert statuses == ["succeeded"] * n


@pytest.mark.asyncio
async def test_concurrent_dataset_item_appends_to_the_same_draft_do_not_lose_updates():
    """Two independent sessions appending to the *same* draft dataset
    version concurrently — a classic read-modify-write race on
    `item_count` if the update isn't atomic at the SQL level."""
    async for session in session_scope():
        repos = RepositoryRegistry(session)
        workspace = await repos.workspaces.add(WorkspaceModel(name="Race Co", organization_id="org-1", slug="race-co"))
        dataset_service = DatasetService(repos)
        dataset = await dataset_service.create_dataset(workspace.id, name="Race Set", owner_id="u1", dataset_type="golden", organization_id="org-1")
        dataset_version_service = DatasetVersionService(repos)
        draft = await dataset_version_service.get_or_create_draft(dataset.id, created_by="u1")
        draft_id = draft.id

    async def append(count: int, offset: int) -> None:
        async for session in session_scope():
            repos = RepositoryRegistry(session)
            version_service = DatasetVersionService(repos)
            await version_service.add_items(draft_id, [
                {"input_data": {"i": offset + i}, "expected_output": str(offset + i)} for i in range(count)
            ])

    await asyncio.gather(append(3, 0), append(4, 100), append(5, 200))

    async for session in session_scope():
        repos = RepositoryRegistry(session)
        version = await repos.dataset_versions.get_or_404(draft_id)
        items = await repos.dataset_items.list_for_version(draft_id)
        assert len(items) == 12
        assert version.item_count == 12  # must reflect every concurrent append, not just the last writer


@pytest.mark.asyncio
async def test_concurrent_benchmark_runs_across_workspaces():
    n = 5

    async def one(i: int) -> str:
        async for session in session_scope():
            repos = RepositoryRegistry(session)
            workspace = await repos.workspaces.add(WorkspaceModel(name=f"Bench Perf {i}", organization_id="org-1", slug=f"bench-perf-{i}"))
            dataset_service = DatasetService(repos)
            dataset_version_service = DatasetVersionService(repos)
            dataset = await dataset_service.create_dataset(workspace.id, name="Set", owner_id="u1", dataset_type="golden", organization_id="org-1")
            draft = await dataset_version_service.get_or_create_draft(dataset.id, created_by="u1")
            await dataset_version_service.add_items(draft.id, [{"input_data": {"q": "1"}, "expected_output": "1"}])
            await dataset_version_service.publish_version(draft.id)
            benchmark_service = BenchmarkService(repos)
            benchmark = await benchmark_service.create_benchmark(
                workspace.id, name="B", owner_id="u1", benchmark_type="model", mode="single",
                organization_id="org-1", dataset_id=dataset.id, metric_keys=["accuracy"],
            )
            benchmark_id = benchmark.id

        from eval_platform.benchmarking.run_service import BenchmarkRunService
        async for session in session_scope():
            repos = RepositoryRegistry(session)
            run_service = BenchmarkRunService(repos)
            run = await run_service.start_run(benchmark_id, [{"label": "c1", "static_response": "1"}], triggered_by="u1")
            run_id = run.id
        async for session in session_scope():
            repos = RepositoryRegistry(session)
            run_service = BenchmarkRunService(repos)
            completed = await run_service.execute_run(run_id, ReferenceTargetExecutor())
            return completed.status

    statuses = await asyncio.gather(*[one(i) for i in range(n)])
    assert statuses == ["succeeded"] * n
