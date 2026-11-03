import json

import pytest

from agent_platform.core.exceptions import DependencyCycleError, RecursionLimitExceededError
from agent_platform.domain.enums import TaskStatus
from agent_platform.models.workspace import WorkspaceModel
from agent_platform.planner.planning_service import PlanningService

from tests.conftest import make_response


def _decomposition_response(subtasks: list[dict], rationale: str = "test rationale") -> str:
    return json.dumps({"rationale": rationale, "subtasks": subtasks})


async def _seed_workspace(repos):
    return await repos.workspaces.add(WorkspaceModel(name="WS", slug="ws-plan", organization_id="org1"))


@pytest.mark.asyncio
async def test_create_root_task_sets_self_as_root(repos, scripted_ai_core):
    context, _ = scripted_ai_core
    ws = await _seed_workspace(repos)
    svc = PlanningService(repos, context)
    task = await svc.create_root_task(ws.id, title="Ship feature X", goal="Ship feature X end to end", created_by="u1")
    assert task.root_task_id == task.id
    assert task.depth == 0
    assert task.status == TaskStatus.PENDING.value


@pytest.mark.asyncio
async def test_decompose_creates_subtasks_with_dependencies(repos, scripted_ai_core):
    context, provider = scripted_ai_core
    ws = await _seed_workspace(repos)
    svc = PlanningService(repos, context)
    root = await svc.create_root_task(ws.id, title="Ship X", goal="Ship X", created_by="u1")

    provider.push(make_response(_decomposition_response([
        {"title": "Design", "goal": "Design X", "priority": "high", "depends_on": [], "estimated_tokens": 1000, "estimated_duration_seconds": 30},
        {"title": "Build", "goal": "Build X", "priority": "normal", "depends_on": [0], "estimated_tokens": 2000, "estimated_duration_seconds": 60},
    ])))

    subtasks = await svc.decompose(root.id)
    assert len(subtasks) == 2
    assert all(t.depth == 1 for t in subtasks)
    assert all(t.root_task_id == root.id for t in subtasks)
    assert all(t.parent_task_id == root.id for t in subtasks)

    refreshed_root = await repos.tasks.get_or_404(root.id)
    assert refreshed_root.status == TaskStatus.PLANNING.value

    deps = await repos.task_dependencies.list_for_task(subtasks[1].id)
    assert len(deps) == 1
    assert deps[0].depends_on_task_id == subtasks[0].id


@pytest.mark.asyncio
async def test_decompose_respects_recursion_limit(repos, scripted_ai_core):
    context, provider = scripted_ai_core
    ws = await _seed_workspace(repos)
    svc = PlanningService(repos, context, max_recursion_depth=1)
    root = await svc.create_root_task(ws.id, title="Root", goal="Root goal", created_by="u1")

    provider.push(make_response(_decomposition_response([
        {"title": "Sub", "goal": "Sub goal", "priority": "normal", "depends_on": [], "estimated_tokens": 100, "estimated_duration_seconds": 5},
    ])))
    subtasks = await svc.decompose(root.id)  # depth 0 -> 1, allowed (max_recursion_depth=1)

    with pytest.raises(RecursionLimitExceededError):
        await svc.decompose(subtasks[0].id)  # depth 1 -> 2, exceeds limit of 1


@pytest.mark.asyncio
async def test_add_dependency_detects_cycle(repos, scripted_ai_core):
    context, provider = scripted_ai_core
    ws = await _seed_workspace(repos)
    svc = PlanningService(repos, context)
    root = await svc.create_root_task(ws.id, title="Root", goal="Root goal", created_by="u1")
    provider.push(make_response(_decomposition_response([
        {"title": "A", "goal": "A", "priority": "normal", "depends_on": [], "estimated_tokens": 100, "estimated_duration_seconds": 5},
        {"title": "B", "goal": "B", "priority": "normal", "depends_on": [], "estimated_tokens": 100, "estimated_duration_seconds": 5},
    ])))
    a, b = await svc.decompose(root.id)
    await svc.add_dependency(b.id, a.id)  # B depends on A — fine
    with pytest.raises(DependencyCycleError):
        await svc.add_dependency(a.id, b.id)  # would create A -> B -> A cycle


@pytest.mark.asyncio
async def test_execution_order_respects_dependencies_and_priority(repos, scripted_ai_core):
    context, provider = scripted_ai_core
    ws = await _seed_workspace(repos)
    svc = PlanningService(repos, context)
    root = await svc.create_root_task(ws.id, title="Root", goal="Root goal", created_by="u1")
    provider.push(make_response(_decomposition_response([
        {"title": "Low-no-dep", "goal": "g", "priority": "low", "depends_on": [], "estimated_tokens": 1, "estimated_duration_seconds": 1},
        {"title": "Critical-no-dep", "goal": "g", "priority": "critical", "depends_on": [], "estimated_tokens": 1, "estimated_duration_seconds": 1},
        {"title": "Depends-on-both", "goal": "g", "priority": "normal", "depends_on": [0, 1], "estimated_tokens": 1, "estimated_duration_seconds": 1},
    ])))
    low, critical, dependent = await svc.decompose(root.id)

    order = await svc.execution_order(root.id)
    # root_task_id itself is included in list_for_root; the dependent task must come after both its deps.
    assert order.index(critical.id) < order.index(dependent.id)
    assert order.index(low.id) < order.index(dependent.id)
    # Among the two ready (no-dependency) tasks, critical priority should be scheduled before low.
    ready_only = [tid for tid in order if tid in (low.id, critical.id)]
    assert ready_only.index(critical.id) < ready_only.index(low.id)


@pytest.mark.asyncio
async def test_estimate_resources_sums_subtasks(repos, scripted_ai_core):
    context, provider = scripted_ai_core
    ws = await _seed_workspace(repos)
    svc = PlanningService(repos, context)
    root = await svc.create_root_task(ws.id, title="Root", goal="Root goal", created_by="u1")
    provider.push(make_response(_decomposition_response([
        {"title": "A", "goal": "g", "priority": "normal", "depends_on": [], "estimated_tokens": 1000, "estimated_duration_seconds": 30},
        {"title": "B", "goal": "g", "priority": "normal", "depends_on": [], "estimated_tokens": 500, "estimated_duration_seconds": 15},
    ])))
    await svc.decompose(root.id)
    estimate = await svc.estimate_resources(root.id)
    assert estimate["subtask_count"] == 2
    assert estimate["estimated_tokens"] == 1500
    assert estimate["estimated_duration_seconds"] == 45.0


@pytest.mark.asyncio
async def test_progress_tracks_completion(repos, scripted_ai_core):
    context, provider = scripted_ai_core
    ws = await _seed_workspace(repos)
    svc = PlanningService(repos, context)
    root = await svc.create_root_task(ws.id, title="Root", goal="Root goal", created_by="u1")
    provider.push(make_response(_decomposition_response([
        {"title": "A", "goal": "g", "priority": "normal", "depends_on": [], "estimated_tokens": 1, "estimated_duration_seconds": 1},
        {"title": "B", "goal": "g", "priority": "normal", "depends_on": [], "estimated_tokens": 1, "estimated_duration_seconds": 1},
    ])))
    a, b = await svc.decompose(root.id)

    empty_progress = await svc.progress(root.id)
    assert empty_progress["percent_complete"] == 0.0

    a.status = TaskStatus.COMPLETED.value
    await repos.tasks.update(a)
    progress = await svc.progress(root.id)
    assert progress["completed"] == 1
    assert progress["total"] == 2
    assert progress["percent_complete"] == 50.0


@pytest.mark.asyncio
async def test_replan_cancels_pending_and_preserves_completed(repos, scripted_ai_core):
    context, provider = scripted_ai_core
    ws = await _seed_workspace(repos)
    svc = PlanningService(repos, context)
    root = await svc.create_root_task(ws.id, title="Root", goal="Root goal", created_by="u1")
    provider.push(make_response(_decomposition_response([
        {"title": "A", "goal": "g", "priority": "normal", "depends_on": [], "estimated_tokens": 1, "estimated_duration_seconds": 1},
        {"title": "B", "goal": "g", "priority": "normal", "depends_on": [], "estimated_tokens": 1, "estimated_duration_seconds": 1},
    ])))
    a, b = await svc.decompose(root.id)
    a.status = TaskStatus.COMPLETED.value
    a.result = {"summary": "done A"}
    await repos.tasks.update(a)

    provider.push(make_response(_decomposition_response([
        {"title": "C (replacement for B)", "goal": "g2", "priority": "high", "depends_on": [], "estimated_tokens": 1, "estimated_duration_seconds": 1},
    ])))
    new_subtasks = await svc.replan(root.id, reason="B's approach failed")

    refreshed_b = await repos.tasks.get_or_404(b.id)
    assert refreshed_b.status == TaskStatus.CANCELLED.value

    refreshed_a = await repos.tasks.get_or_404(a.id)
    assert refreshed_a.status == TaskStatus.COMPLETED.value  # untouched

    assert len(new_subtasks) == 1
    assert new_subtasks[0].title.startswith("C")
