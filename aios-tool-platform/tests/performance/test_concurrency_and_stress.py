"""Performance/stress/concurrency tests — the category the rest of the
suite (correctness-focused, small fixed inputs) deliberately doesn't
cover. Three different kinds of concurrency are exercised, matching the
concurrency models the platform actually has:

1. Many independent tool calls, each with its OWN AsyncSession/Engine —
   the shape real concurrent API traffic takes (every FastAPI request
   gets a fresh session; see `dependencies/dependencies.py`). Proves the
   platform doesn't corrupt state under genuine multi-connection load
   against the same WAL-mode SQLite file.
2. `run_batch(execution_mode="parallel")` high fan-out inside ONE
   execution/session — proves the engine's `_session_lock` design
   (repo access locked, `handler.execute()` calls unlocked) delivers
   real wall-clock concurrency, not serialization dressed up as
   "parallel."
3. Concurrent sensitive-tool approval decisions across independent
   executions, and a high-volume scheduler dispatch / stalled-execution
   recovery sweep — both correctness-tested elsewhere against 1-3 rows
   but never at a realistic batch size."""
from __future__ import annotations

import asyncio
import time
from datetime import timedelta

import pytest

from tests.performance.conftest import make_committed_tool, make_committed_workspace, new_engine, new_repos
from tool_platform.domain.enums import ExecutionStatus
from tool_platform.governance.approval_service import ApprovalService
from tool_platform.config.settings import get_settings
from tool_platform.governance.policy_engine import PolicyEngine
from tool_platform.models.execution import ToolExecutionModel
from tool_platform.scheduler.dispatcher import ScheduleDispatcher
from tool_platform.scheduler.schedule_service import ScheduleService
from tool_platform.tool_execution.handlers.base import ConnectorHandler
from tool_platform.tool_execution.registry import ConnectorRegistry

CONCURRENCY = 20


class SlowHandler(ConnectorHandler):
    def __init__(self, *, delay: float):
        self.delay = delay

    async def execute(self, ctx):
        await asyncio.sleep(self.delay)
        return dict(ctx.input_data)

    async def compensate(self, ctx) -> None:
        return None


@pytest.mark.asyncio
async def test_many_concurrent_independent_executions_same_tool():
    """N callers hitting the same published tool at once, each through its
    own session — approximates N simultaneous `POST /executions`
    requests. Every call must complete correctly and land its own
    isolated execution row; nothing should be dropped, duplicated, or
    cross-contaminated between calls."""
    workspace = await make_committed_workspace(name="Concurrent Exec Co")
    tool = await make_committed_tool(workspace.id, name="Concurrent Tool")

    async def run_once(i: int):
        repos = new_repos()
        try:
            engine = new_engine(repos)
            execution = await engine.start_execution(tool.id, input_data={"i": i}, triggered_by=f"user-{i}")
            await repos.session.commit()
            return execution
        finally:
            await repos.session.close()

    results = await asyncio.gather(*(run_once(i) for i in range(CONCURRENCY)))

    assert len(results) == CONCURRENCY
    assert all(e.status == ExecutionStatus.SUCCEEDED.value for e in results)
    assert len({e.id for e in results}) == CONCURRENCY

    verify_repos = new_repos()
    try:
        all_executions = await verify_repos.executions.list_for_tool(tool.id, limit=1000)
        assert len(all_executions) == CONCURRENCY
        assert all(e.status == ExecutionStatus.SUCCEEDED.value for e in all_executions)
    finally:
        await verify_repos.session.close()


@pytest.mark.asyncio
async def test_run_batch_parallel_high_fanout_is_genuinely_concurrent(repos, workspace, tool_service, version_service):
    """16 branches that each sleep 0.05s. If run_batch(parallel) actually
    ran them concurrently (as the engine's unlocked-handler-execution
    design intends), total wall time should be close to one branch's
    delay, not sixteen of them stacked up serially."""
    from tests.execution.conftest import make_published_tool

    branch_count = 16
    branch_seconds = 0.05
    connectors = ConnectorRegistry({"slow": SlowHandler(delay=branch_seconds)})
    tool, _version = await make_published_tool(tool_service, version_service, workspace, connector_key="slow")
    engine = new_engine(repos, connectors)

    started = time.monotonic()
    parent, children = await engine.run_batch(tool.id, [{"i": i} for i in range(branch_count)], execution_mode="parallel")
    elapsed = time.monotonic() - started

    assert parent.status == ExecutionStatus.SUCCEEDED.value
    assert len(children) == branch_count
    assert all(c.status == ExecutionStatus.SUCCEEDED.value for c in children)
    # Serial execution would take >= branch_count * branch_seconds (0.8s); true
    # concurrency should land close to a single branch's delay. Generous
    # margin to keep this stable under CI/sandbox scheduling jitter.
    assert elapsed < branch_count * branch_seconds * 0.75


@pytest.mark.asyncio
async def test_scheduler_dispatch_high_volume(repos, workspace, tool_service, version_service):
    """30 immediate schedules against one tool, dispatched in a single
    `tick()` call — a throughput/volume check the correctness-focused
    scheduler tests (1-2 schedules) don't exercise."""
    from tests.execution.conftest import make_published_tool

    tool, _version = await make_published_tool(tool_service, version_service, workspace, connector_key="echo")
    schedule_service = ScheduleService(repos)
    engine = new_engine(repos)
    dispatcher = ScheduleDispatcher(repos, engine)

    batch_size = 30
    for i in range(batch_size):
        await schedule_service.create_immediate(tool.id, workspace.id, created_by=f"u{i}")

    fired = await dispatcher.tick(limit=100)
    assert len(fired) == batch_size
    assert all(e.status == ExecutionStatus.SUCCEEDED.value for e in fired)

    # A second tick should fire nothing more — IMMEDIATE schedules are one-shot.
    fired_again = await dispatcher.tick(limit=100)
    assert fired_again == []


@pytest.mark.asyncio
async def test_recovery_sweep_handles_many_stalled_executions(repos, workspace, tool_service, version_service):
    """25 executions stuck RUNNING past the stall threshold, interleaved
    with a few genuinely-fresh ones — the sweep must cancel every stale
    one and leave the fresh ones alone, in a single pass."""
    from tests.execution.conftest import make_published_tool
    from tool_platform.database.base import utcnow

    tool, version = await make_published_tool(tool_service, version_service, workspace, connector_key="echo")

    stale_count, fresh_count = 25, 5
    for _ in range(stale_count):
        await repos.executions.add(ToolExecutionModel(
            tool_id=tool.id, tool_version_id=version.id, workspace_id=workspace.id,
            status=ExecutionStatus.RUNNING.value, started_at=utcnow() - timedelta(hours=2), triggered_by="u1",
        ))
    for _ in range(fresh_count):
        await repos.executions.add(ToolExecutionModel(
            tool_id=tool.id, tool_version_id=version.id, workspace_id=workspace.id,
            status=ExecutionStatus.RUNNING.value, started_at=utcnow(), triggered_by="u1",
        ))

    engine = new_engine(repos)
    recovered = await engine.sweep_stalled_executions(stalled_after_seconds=3600)
    assert len(recovered) == stale_count
    assert all(e.status == ExecutionStatus.CANCELLED.value for e in recovered)

    all_executions = await repos.executions.list_for_tool(tool.id, limit=1000)
    still_running = [e for e in all_executions if e.status == ExecutionStatus.RUNNING.value]
    assert len(still_running) == fresh_count


@pytest.mark.asyncio
async def test_concurrent_approval_decisions_across_independent_executions():
    """K sensitive-tool calls independently blocked on an approval gate,
    all decided and executed concurrently (each through its own
    session/engine, mirroring K reviewers clicking "approve" around the
    same moment) — every decision must resolve its own execution to
    SUCCEEDED without interfering with the others."""
    workspace = await make_committed_workspace(name="Approval Concurrency Co")
    tool = await make_committed_tool(workspace.id, name="Sensitive Tool", sensitivity_level="critical")

    k = 10

    async def request_and_approve(i: int) -> str:
        repos = new_repos()
        try:
            approval_service = ApprovalService(repos)
            gate = await approval_service.request_approval("tool", tool.id, requested_by=f"user-{i}")
            approved = await approval_service.approve(gate.id, approver_id="admin-1")
            await repos.session.commit()
            return approved.id
        finally:
            await repos.session.close()

    gate_ids = await asyncio.gather(*(request_and_approve(i) for i in range(k)))

    async def execute_with_gate(gate_id: str, i: int) -> str:
        repos = new_repos()
        try:
            engine = new_engine(
                repos, policy_engine=PolicyEngine(repos, get_settings()), approval_service=ApprovalService(repos),
            )
            execution = await engine.start_execution(tool.id, triggered_by=f"user-{i}", approval_gate_id=gate_id)
            await repos.session.commit()
            return execution.status
        finally:
            await repos.session.close()

    statuses = await asyncio.gather(*(execute_with_gate(gid, i) for i, gid in enumerate(gate_ids)))
    assert all(status == ExecutionStatus.SUCCEEDED.value for status in statuses)

    verify_repos = new_repos()
    try:
        all_executions = await verify_repos.executions.list_for_tool(tool.id, limit=1000)
        assert len(all_executions) == k
        assert all(e.status == ExecutionStatus.SUCCEEDED.value for e in all_executions)
    finally:
        await verify_repos.session.close()
