"""Performance/stress/concurrency tests — the category the rest of the
suite (correctness-focused, small fixed graphs) deliberately doesn't
cover. Two different kinds of concurrency are exercised here, matching
the two different concurrency models the engine actually has:

1. Many independent executions, each with its OWN AsyncSession/Engine —
   the shape real concurrent API traffic takes (every FastAPI request
   gets a fresh session; see `workflow_api/dependencies.py`). Proves the
   platform doesn't corrupt state under genuine multi-connection load
   against the same WAL-mode SQLite file.
2. PARALLEL_BRANCH fan-out inside ONE execution/session — proves the
   engine's `_session_lock` design (repo access locked, `handler.execute()`
   calls unlocked) delivers real wall-clock concurrency, not serialization
   dressed up as a "parallel" node type.

Plus throughput/volume checks for the scheduler dispatcher and the
stalled-execution recovery sweep, both of which are correctness-tested
elsewhere against 1-2 rows but never against a realistic batch size.
"""
from __future__ import annotations

import asyncio
import time
from datetime import timedelta

import pytest

from tests.performance.conftest import make_committed_linear_workflow, make_committed_workspace, new_engine, new_repos
from workflow_platform.ai_bridges.reference_bridges import build_reference_bridge_set
from workflow_platform.database.base import utcnow
from workflow_platform.domain.enums import ApprovalStatus, ExecutionStatus
from workflow_platform.models.checkpoint import CheckpointModel
from workflow_platform.models.execution import ExecutionModel
from workflow_platform.models.workspace import WorkspaceModel
from workflow_platform.node_library.registry import seed_node_definitions
from workflow_platform.recovery.recovery_service import RecoveryService
from workflow_platform.scheduler.dispatcher import SchedulerDispatcher
from workflow_platform.scheduler.scheduler_service import ScheduleService
from workflow_platform.workflow_core.version_service import WorkflowVersionService
from workflow_platform.workflow_core.workflow_service import WorkflowService
from workflow_platform.workflow_engine.engine import ExecutionEngine
from workflow_platform.workflow_engine.registry import build_default_handler_registry


CONCURRENCY = 20


@pytest.mark.asyncio
async def test_many_concurrent_independent_executions_same_workflow():
    """N callers hitting the same published workflow at once, each through
    its own session — approximates N simultaneous `POST /executions`
    requests. Every run must complete correctly and land its own
    isolated node_execution rows; nothing should be dropped, duplicated,
    or cross-contaminated between runs."""
    workspace = await make_committed_workspace(name="Concurrent Exec Co")
    wf = await make_committed_linear_workflow(workspace.id, name="Concurrent WF", seconds=0.01)

    async def run_once(i: int):
        repos = new_repos()
        try:
            engine = new_engine(repos)
            execution = await engine.start_execution(wf.id, triggered_by=f"user-{i}")
            await repos.session.commit()
            return execution
        finally:
            await repos.session.close()

    results = await asyncio.gather(*(run_once(i) for i in range(CONCURRENCY)))

    assert len(results) == CONCURRENCY
    assert all(e.status == ExecutionStatus.COMPLETED.value for e in results)
    assert len({e.id for e in results}) == CONCURRENCY  # every execution got its own id

    verify_repos = new_repos()
    try:
        all_executions = await verify_repos.executions.list_for_workflow(wf.id, limit=1000)
        assert len(all_executions) == CONCURRENCY
        assert all(e.status == ExecutionStatus.COMPLETED.value for e in all_executions)
        for execution in all_executions:
            node_execs = await verify_repos.node_executions.list_for_execution(execution.id)
            assert {ne.node_key for ne in node_execs} == {"start", "delay", "end"}
    finally:
        await verify_repos.session.close()


@pytest.mark.asyncio
async def test_parallel_branch_high_fanout_is_genuinely_concurrent(repos):
    """8 branches that each sleep 0.05s. If PARALLEL_BRANCH actually ran
    them concurrently (as the engine's unlocked-handler-execution design
    intends), total wall time should be close to one branch's delay, not
    eight of them stacked up serially."""
    await seed_node_definitions(repos)
    workspace = await repos.workspaces.add(WorkspaceModel(name="Fanout Co", organization_id="org-1", slug="fanout-co"))
    workflow_service = WorkflowService(repos)
    version_service = WorkflowVersionService(repos)
    wf = await workflow_service.create_workflow(workspace.id, name="Fanout WF", owner_id="u1", category="automation")

    branch_count = 8
    branch_seconds = 0.05
    draft = await version_service.get_or_create_draft(wf.id, created_by="u1")
    await version_service.add_node(draft.id, node_key="start", node_type="start", name="Start")
    await version_service.add_node(draft.id, node_key="fan_out", node_type="parallel_branch", name="Fan Out")
    await version_service.add_node(draft.id, node_key="join", node_type="merge", name="Join")
    await version_service.add_node(draft.id, node_key="end", node_type="end", name="End")
    await version_service.add_edge(draft.id, source_node_key="start", target_node_key="fan_out")
    await version_service.add_edge(draft.id, source_node_key="join", target_node_key="end")
    for i in range(branch_count):
        key = f"branch_{i}"
        await version_service.add_node(draft.id, node_key=key, node_type="delay", name=key, config={"seconds": branch_seconds})
        await version_service.add_edge(draft.id, source_node_key="fan_out", target_node_key=key)
        await version_service.add_edge(draft.id, source_node_key=key, target_node_key="join")
    await version_service.publish_version(draft.id)

    bridges_registry = build_default_handler_registry(bridges=build_reference_bridge_set())
    engine = ExecutionEngine(repos, bridges_registry)

    started = time.monotonic()
    execution = await engine.start_execution(wf.id, triggered_by="u1")
    elapsed = time.monotonic() - started

    assert execution.status == ExecutionStatus.COMPLETED.value
    node_execs = await repos.node_executions.list_for_execution(execution.id)
    assert {ne.node_key for ne in node_execs if ne.node_key.startswith("branch_")} == {f"branch_{i}" for i in range(branch_count)}
    # Serial execution would take >= branch_count * branch_seconds (0.4s); true
    # concurrency should land close to a single branch's delay. Generous
    # margin to keep this stable under CI/sandbox scheduling jitter.
    assert elapsed < branch_count * branch_seconds * 0.75


@pytest.mark.asyncio
async def test_scheduler_dispatch_high_volume(repos):
    """30 immediate schedules against one workflow, dispatched in a single
    `tick()` call — a throughput/volume check the correctness-focused
    scheduler tests (1-2 schedules) don't exercise."""
    await seed_node_definitions(repos)
    workspace = await repos.workspaces.add(WorkspaceModel(name="Dispatch Co", organization_id="org-1", slug="dispatch-co"))
    workflow_service = WorkflowService(repos)
    version_service = WorkflowVersionService(repos)
    wf = await workflow_service.create_workflow(workspace.id, name="Dispatch WF", owner_id="u1", category="automation")
    draft = await version_service.get_or_create_draft(wf.id, created_by="u1")
    await version_service.add_node(draft.id, node_key="start", node_type="start", name="Start")
    await version_service.add_node(draft.id, node_key="end", node_type="end", name="End")
    await version_service.add_edge(draft.id, source_node_key="start", target_node_key="end")
    await version_service.publish_version(draft.id)

    schedule_service = ScheduleService(repos)
    bridges = build_reference_bridge_set()
    engine = ExecutionEngine(repos, build_default_handler_registry(bridges=bridges))
    dispatcher = SchedulerDispatcher(repos, engine)

    batch_size = 30
    for i in range(batch_size):
        await schedule_service.create_immediate(wf.id, workspace.id, created_by=f"u{i}")

    fired = await dispatcher.tick(limit=100)
    assert len(fired) == batch_size
    assert all(e.status == ExecutionStatus.COMPLETED.value for e in fired)

    # A second tick should fire nothing more — IMMEDIATE schedules are one-shot.
    fired_again = await dispatcher.tick(limit=100)
    assert fired_again == []


@pytest.mark.asyncio
async def test_recovery_sweep_handles_many_stalled_executions(repos):
    """30 executions stuck RUNNING past the stall threshold, interleaved
    with a few genuinely-fresh ones — the sweep must pause every stale
    one and leave the fresh ones alone, in a single pass."""
    await seed_node_definitions(repos)
    workspace = await repos.workspaces.add(WorkspaceModel(name="Recovery Stress Co", organization_id="org-1", slug="recovery-stress-co"))
    workflow_service = WorkflowService(repos)
    version_service = WorkflowVersionService(repos)
    wf = await workflow_service.create_workflow(workspace.id, name="Recovery Stress WF", owner_id="u1", category="automation")
    draft = await version_service.get_or_create_draft(wf.id, created_by="u1")
    await version_service.add_node(draft.id, node_key="start", node_type="start", name="Start")
    await version_service.add_node(draft.id, node_key="step", node_type="delay", name="Step", config={"seconds": 0})
    await version_service.add_node(draft.id, node_key="end", node_type="end", name="End")
    await version_service.add_edge(draft.id, source_node_key="start", target_node_key="step")
    await version_service.add_edge(draft.id, source_node_key="step", target_node_key="end")
    version = await version_service.publish_version(draft.id)

    stale_count, fresh_count = 25, 5
    for _ in range(stale_count):
        execution = await repos.executions.add(ExecutionModel(
            workflow_id=wf.id, workflow_version_id=version.id, workspace_id=workspace.id,
            status=ExecutionStatus.RUNNING.value, current_node_key="step", triggered_by="u1",
        ))
        checkpoint = await repos.checkpoints.add(CheckpointModel(
            execution_id=execution.id, node_key="start", sequence_number=1,
            state_snapshot={"context_variables": {}, "current_node_key": "step"},
        ))
        checkpoint.created_at = utcnow() - timedelta(hours=2)
        await repos.checkpoints.update(checkpoint)
    for _ in range(fresh_count):
        await repos.executions.add(ExecutionModel(
            workflow_id=wf.id, workflow_version_id=version.id, workspace_id=workspace.id,
            status=ExecutionStatus.RUNNING.value, current_node_key="step", triggered_by="u1",
        ))

    recovery = RecoveryService(repos)
    recovered = await recovery.recover_stalled_executions(stalled_after_seconds=3600)
    assert len(recovered) == stale_count
    assert all(e.status == ExecutionStatus.PAUSED.value for e in recovered)

    all_executions = await repos.executions.list_for_workflow(wf.id, limit=1000)
    still_running = [e for e in all_executions if e.status == ExecutionStatus.RUNNING.value]
    assert len(still_running) == fresh_count


@pytest.mark.asyncio
async def test_concurrent_approval_decisions_across_independent_executions():
    """K executions independently paused at an APPROVAL node, all decided
    concurrently (each through its own session/engine, mirroring K
    reviewers clicking "approve" around the same moment) — every decision
    must resolve its own execution to COMPLETED without interfering with
    the others."""
    from workflow_platform.approval.approval_service import ApprovalService

    workspace = await make_committed_workspace(name="Approval Concurrency Co")

    repos = new_repos()
    try:
        workflow_service = WorkflowService(repos)
        version_service = WorkflowVersionService(repos)
        wf = await workflow_service.create_workflow(workspace.id, name="Approval Concurrency WF", owner_id="u1", category="automation")
        draft = await version_service.get_or_create_draft(wf.id, created_by="u1")
        await version_service.add_node(draft.id, node_key="start", node_type="start", name="Start")
        await version_service.add_node(draft.id, node_key="gate", node_type="approval", name="Gate", config={"approval_chain": [["approver-1"]]})
        await version_service.add_node(draft.id, node_key="end", node_type="end", name="End")
        await version_service.add_edge(draft.id, source_node_key="start", target_node_key="gate")
        await version_service.add_edge(draft.id, source_node_key="gate", target_node_key="end")
        await version_service.publish_version(draft.id)
        await repos.session.commit()
    finally:
        await repos.session.close()

    k = 10

    async def start_and_pause(i: int) -> str:
        repos = new_repos()
        try:
            engine = new_engine(repos)
            execution = await engine.start_execution(wf.id, triggered_by=f"requester-{i}")
            await repos.session.commit()
            assert execution.status == ExecutionStatus.WAITING_APPROVAL.value
            return execution.id
        finally:
            await repos.session.close()

    execution_ids = await asyncio.gather(*(start_and_pause(i) for i in range(k)))

    async def decide(execution_id: str):
        repos = new_repos()
        try:
            engine = new_engine(repos)
            approvals = await repos.approval_requests.list_for_execution(execution_id)
            approval = approvals[0]
            approval_service = ApprovalService(repos, engine=engine)
            decided = await approval_service.approve_step(approval.id, decided_by="approver-1")
            await repos.session.commit()
            return decided.status
        finally:
            await repos.session.close()

    decisions = await asyncio.gather(*(decide(eid) for eid in execution_ids))
    assert all(status == ApprovalStatus.APPROVED.value for status in decisions)

    verify_repos = new_repos()
    try:
        for eid in execution_ids:
            execution = await verify_repos.executions.get_or_404(eid)
            assert execution.status == ExecutionStatus.COMPLETED.value
    finally:
        await verify_repos.session.close()
