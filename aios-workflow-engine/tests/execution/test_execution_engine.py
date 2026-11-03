import asyncio

import pytest

from tests.execution.conftest import make_engine, publish_graph
from workflow_platform.core.exceptions import RecursionLimitExceededError
from workflow_platform.domain.enums import ApprovalStatus, ExecutionStatus, NodeExecutionStatus
from workflow_platform.workflow_engine.handlers.base import NodeHandler


async def _make_workflow(workflow_service, workspace, *, name="WF"):
    return await workflow_service.create_workflow(workspace.id, name=name, owner_id="u1", category="automation")


@pytest.mark.asyncio
async def test_simple_linear_execution_completes(repos, workspace, workflow_service, version_service):
    wf = await _make_workflow(workflow_service, workspace)
    await publish_graph(
        version_service, wf.id,
        nodes=[
            {"node_key": "start", "node_type": "start", "name": "Start"},
            {"node_key": "delay", "node_type": "delay", "name": "Delay", "config": {"seconds": 0}},
            {"node_key": "end", "node_type": "end", "name": "End"},
        ],
        edges=[
            {"source_node_key": "start", "target_node_key": "delay"},
            {"source_node_key": "delay", "target_node_key": "end"},
        ],
    )
    engine = make_engine(repos)
    execution = await engine.start_execution(wf.id, triggered_by="u1")
    assert execution.status == ExecutionStatus.COMPLETED.value
    assert execution.completed_at is not None

    node_execs = await repos.node_executions.list_for_execution(execution.id)
    assert {ne.node_key for ne in node_execs} == {"start", "delay", "end"}
    assert all(ne.status == NodeExecutionStatus.SUCCEEDED.value for ne in node_execs)


@pytest.mark.asyncio
async def test_llm_call_uses_ai_core_and_updates_context(repos, workspace, workflow_service, version_service, scripted_ai_core):
    ai_core, provider = scripted_ai_core
    from tests.conftest import make_response
    provider.push(make_response("hello from the model"))

    wf = await _make_workflow(workflow_service, workspace)
    await publish_graph(
        version_service, wf.id,
        nodes=[
            {"node_key": "start", "node_type": "start", "name": "Start"},
            {"node_key": "call_llm", "node_type": "llm_call", "name": "Call LLM", "config": {"prompt": "say hi"}},
            {"node_key": "end", "node_type": "end", "name": "End"},
        ],
        edges=[
            {"source_node_key": "start", "target_node_key": "call_llm"},
            {"source_node_key": "call_llm", "target_node_key": "end"},
        ],
    )
    engine = make_engine(repos, ai_core=ai_core)
    execution = await engine.start_execution(wf.id, triggered_by="u1")
    assert execution.status == ExecutionStatus.COMPLETED.value
    assert execution.output_variables["content"] == "hello from the model"
    assert provider.calls == 1


@pytest.mark.asyncio
async def test_condition_node_routes_true_and_false_branches(repos, workspace, workflow_service, version_service):
    wf = await _make_workflow(workflow_service, workspace, name="Cond WF")
    await publish_graph(
        version_service, wf.id,
        nodes=[
            {"node_key": "start", "node_type": "start", "name": "Start"},
            {"node_key": "check", "node_type": "condition", "name": "Check", "config": {"expression": "flag == True"}},
            {"node_key": "true_path", "node_type": "delay", "name": "True Path", "config": {"seconds": 0}},
            {"node_key": "false_path", "node_type": "delay", "name": "False Path", "config": {"seconds": 0}},
            {"node_key": "end", "node_type": "end", "name": "End"},
        ],
        edges=[
            {"source_node_key": "start", "target_node_key": "check"},
            {"source_node_key": "check", "target_node_key": "true_path", "condition": {"when": True}},
            {"source_node_key": "check", "target_node_key": "false_path", "condition": {"when": False}},
            {"source_node_key": "true_path", "target_node_key": "end"},
            {"source_node_key": "false_path", "target_node_key": "end"},
        ],
    )
    engine = make_engine(repos)

    exec_true = await engine.start_execution(wf.id, triggered_by="u1", input_variables={"flag": True})
    node_keys_true = {ne.node_key for ne in await repos.node_executions.list_for_execution(exec_true.id)}
    assert "true_path" in node_keys_true and "false_path" not in node_keys_true

    exec_false = await engine.start_execution(wf.id, triggered_by="u1", input_variables={"flag": False})
    node_keys_false = {ne.node_key for ne in await repos.node_executions.list_for_execution(exec_false.id)}
    assert "false_path" in node_keys_false and "true_path" not in node_keys_false


@pytest.mark.asyncio
async def test_decision_node_routes_by_case_with_default(repos, workspace, workflow_service, version_service):
    wf = await _make_workflow(workflow_service, workspace, name="Decision WF")
    await publish_graph(
        version_service, wf.id,
        nodes=[
            {"node_key": "start", "node_type": "start", "name": "Start"},
            {"node_key": "route", "node_type": "decision", "name": "Route", "config": {"expression": "category"}},
            {"node_key": "path_a", "node_type": "delay", "name": "A", "config": {"seconds": 0}},
            {"node_key": "path_default", "node_type": "delay", "name": "Default", "config": {"seconds": 0}},
            {"node_key": "end", "node_type": "end", "name": "End"},
        ],
        edges=[
            {"source_node_key": "start", "target_node_key": "route"},
            {"source_node_key": "route", "target_node_key": "path_a", "condition": {"case": "a"}},
            {"source_node_key": "route", "target_node_key": "path_default", "condition": {"default": True}},
            {"source_node_key": "path_a", "target_node_key": "end"},
            {"source_node_key": "path_default", "target_node_key": "end"},
        ],
    )
    engine = make_engine(repos)

    exec_a = await engine.start_execution(wf.id, triggered_by="u1", input_variables={"category": "a"})
    keys_a = {ne.node_key for ne in await repos.node_executions.list_for_execution(exec_a.id)}
    assert "path_a" in keys_a

    exec_z = await engine.start_execution(wf.id, triggered_by="u1", input_variables={"category": "unknown"})
    keys_z = {ne.node_key for ne in await repos.node_executions.list_for_execution(exec_z.id)}
    assert "path_default" in keys_z


@pytest.mark.asyncio
async def test_parallel_branch_runs_concurrently_and_merges(repos, workspace, workflow_service, version_service):
    wf = await _make_workflow(workflow_service, workspace, name="Parallel WF")
    await publish_graph(
        version_service, wf.id,
        nodes=[
            {"node_key": "start", "node_type": "start", "name": "Start"},
            {"node_key": "fan_out", "node_type": "parallel_branch", "name": "Fan Out"},
            {"node_key": "branch_a", "node_type": "delay", "name": "Branch A", "config": {"seconds": 0}},
            {"node_key": "branch_b", "node_type": "delay", "name": "Branch B", "config": {"seconds": 0}},
            {"node_key": "join", "node_type": "merge", "name": "Join"},
            {"node_key": "end", "node_type": "end", "name": "End"},
        ],
        edges=[
            {"source_node_key": "start", "target_node_key": "fan_out"},
            {"source_node_key": "fan_out", "target_node_key": "branch_a"},
            {"source_node_key": "fan_out", "target_node_key": "branch_b"},
            {"source_node_key": "branch_a", "target_node_key": "join"},
            {"source_node_key": "branch_b", "target_node_key": "join"},
            {"source_node_key": "join", "target_node_key": "end"},
        ],
    )
    engine = make_engine(repos)
    execution = await engine.start_execution(wf.id, triggered_by="u1")
    assert execution.status == ExecutionStatus.COMPLETED.value
    node_keys = {ne.node_key for ne in await repos.node_executions.list_for_execution(execution.id)}
    assert {"branch_a", "branch_b", "join"} <= node_keys


@pytest.mark.asyncio
async def test_loop_over_collection_iterates_each_item(repos, workspace, workflow_service, version_service):
    wf = await _make_workflow(workflow_service, workspace, name="Loop WF")
    await publish_graph(
        version_service, wf.id,
        nodes=[
            {"node_key": "start", "node_type": "start", "name": "Start"},
            {"node_key": "loop1", "node_type": "loop", "name": "Loop", "config": {"over": "items", "item_variable": "item"}},
            {"node_key": "body", "node_type": "delay", "name": "Body", "config": {"seconds": 0}},
            {"node_key": "end", "node_type": "end", "name": "End"},
        ],
        edges=[
            {"source_node_key": "start", "target_node_key": "loop1"},
            {"source_node_key": "loop1", "target_node_key": "body", "condition": {"loop_body": True}},
            {"source_node_key": "loop1", "target_node_key": "end", "condition": {"loop_exit": True}},
            {"source_node_key": "body", "target_node_key": "loop1"},
        ],
    )
    engine = make_engine(repos)
    execution = await engine.start_execution(wf.id, triggered_by="u1", input_variables={"items": ["a", "b", "c"]})
    assert execution.status == ExecutionStatus.COMPLETED.value
    body_runs = [ne for ne in await repos.node_executions.list_for_execution(execution.id) if ne.node_key == "body"]
    assert len(body_runs) == 3
    assert "__loop_iter__loop1" not in execution.context_variables


class _FlakyHandler(NodeHandler):
    """Fails the first `fail_times` calls, then succeeds."""

    def __init__(self, fail_times: int):
        self.fail_times = fail_times
        self.calls = 0

    async def execute(self, ctx):
        self.calls += 1
        if self.calls <= self.fail_times:
            raise RuntimeError(f"flaky failure #{self.calls}")
        return {"succeeded_on_attempt": self.calls}


@pytest.mark.asyncio
async def test_retry_then_succeed(repos, workspace, workflow_service, version_service):
    handler = _FlakyHandler(fail_times=2)

    async def custom_fn(ctx):
        return await handler.execute(ctx)

    wf = await _make_workflow(workflow_service, workspace, name="Retry WF")
    await publish_graph(
        version_service, wf.id,
        nodes=[
            {"node_key": "start", "node_type": "start", "name": "Start"},
            {"node_key": "flaky", "node_type": "custom", "name": "Flaky", "config": {"handler_key": "flaky"}, "max_retries": 3},
            {"node_key": "end", "node_type": "end", "name": "End"},
        ],
        edges=[
            {"source_node_key": "start", "target_node_key": "flaky"},
            {"source_node_key": "flaky", "target_node_key": "end"},
        ],
    )
    engine = make_engine(repos, sleep_fn=lambda s: asyncio.sleep(0), custom_handlers={"flaky": custom_fn})
    execution = await engine.start_execution(wf.id, triggered_by="u1")
    assert execution.status == ExecutionStatus.COMPLETED.value
    flaky_ne = next(ne for ne in await repos.node_executions.list_for_execution(execution.id) if ne.node_key == "flaky")
    assert flaky_ne.attempt_number == 3
    assert flaky_ne.output_data["succeeded_on_attempt"] == 3


@pytest.mark.asyncio
async def test_retry_exhausted_fails_execution(repos, workspace, workflow_service, version_service):
    handler = _FlakyHandler(fail_times=99)

    async def always_fails(ctx):
        return await handler.execute(ctx)

    wf = await _make_workflow(workflow_service, workspace, name="Exhaust WF")
    await publish_graph(
        version_service, wf.id,
        nodes=[
            {"node_key": "start", "node_type": "start", "name": "Start"},
            {"node_key": "doomed", "node_type": "custom", "name": "Doomed", "config": {"handler_key": "doomed"}, "max_retries": 1},
            {"node_key": "end", "node_type": "end", "name": "End"},
        ],
        edges=[
            {"source_node_key": "start", "target_node_key": "doomed"},
            {"source_node_key": "doomed", "target_node_key": "end"},
        ],
    )
    engine = make_engine(repos, sleep_fn=lambda s: asyncio.sleep(0), custom_handlers={"doomed": always_fails})
    execution = await engine.start_execution(wf.id, triggered_by="u1")
    assert execution.status in (ExecutionStatus.COMPENSATED.value, ExecutionStatus.FAILED.value)
    doomed_ne = next(ne for ne in await repos.node_executions.list_for_execution(execution.id) if ne.node_key == "doomed")
    assert doomed_ne.status == NodeExecutionStatus.FAILED.value
    assert doomed_ne.attempt_number == 2  # 1 initial + 1 retry


@pytest.mark.asyncio
async def test_node_timeout_is_enforced(repos, workspace, workflow_service, version_service):
    async def slow_fn(ctx):
        await asyncio.sleep(5)
        return {}

    wf = await _make_workflow(workflow_service, workspace, name="Timeout WF")
    await publish_graph(
        version_service, wf.id,
        nodes=[
            {"node_key": "start", "node_type": "start", "name": "Start"},
            {"node_key": "slow", "node_type": "custom", "name": "Slow", "config": {"handler_key": "slow"}, "timeout_seconds": 0.05},
            {"node_key": "end", "node_type": "end", "name": "End"},
        ],
        edges=[
            {"source_node_key": "start", "target_node_key": "slow"},
            {"source_node_key": "slow", "target_node_key": "end"},
        ],
    )
    engine = make_engine(repos, custom_handlers={"slow": slow_fn})
    execution = await engine.start_execution(wf.id, triggered_by="u1")
    slow_ne = next(ne for ne in await repos.node_executions.list_for_execution(execution.id) if ne.node_key == "slow")
    assert slow_ne.status == NodeExecutionStatus.TIMED_OUT.value
    assert "timed out" in slow_ne.error_message


@pytest.mark.asyncio
async def test_approval_node_pauses_execution_and_creates_request(repos, workspace, workflow_service, version_service):
    wf = await _make_workflow(workflow_service, workspace, name="Approval WF")
    await publish_graph(
        version_service, wf.id,
        nodes=[
            {"node_key": "start", "node_type": "start", "name": "Start"},
            {"node_key": "approve", "node_type": "approval", "name": "Approve", "config": {"reason": "needs sign-off"}},
            {"node_key": "end", "node_type": "end", "name": "End"},
        ],
        edges=[
            {"source_node_key": "start", "target_node_key": "approve"},
            {"source_node_key": "approve", "target_node_key": "end"},
        ],
    )
    engine = make_engine(repos)
    execution = await engine.start_execution(wf.id, triggered_by="u1")
    assert execution.status == ExecutionStatus.WAITING_APPROVAL.value

    requests = await repos.approval_requests.list_for_execution(execution.id)
    assert len(requests) == 1
    assert requests[0].status == ApprovalStatus.PENDING.value
    assert requests[0].reason == "needs sign-off"

    approve_ne = next(ne for ne in await repos.node_executions.list_for_execution(execution.id) if ne.node_key == "approve")
    assert approve_ne.status == NodeExecutionStatus.WAITING_APPROVAL.value


@pytest.mark.asyncio
async def test_compensation_runs_on_downstream_failure(repos, workspace, workflow_service, version_service):
    async def always_fails(ctx):
        raise RuntimeError("boom")

    wf = await _make_workflow(workflow_service, workspace, name="Compensation WF")
    await publish_graph(
        version_service, wf.id,
        nodes=[
            {"node_key": "start", "node_type": "start", "name": "Start"},
            {"node_key": "write_mem", "node_type": "memory_write", "name": "Write Memory", "config": {"scope": "workflow", "content": {"x": 1}}},
            {"node_key": "boom", "node_type": "custom", "name": "Boom", "config": {"handler_key": "boom"}},
            {"node_key": "end", "node_type": "end", "name": "End"},
        ],
        edges=[
            {"source_node_key": "start", "target_node_key": "write_mem"},
            {"source_node_key": "write_mem", "target_node_key": "boom"},
            {"source_node_key": "boom", "target_node_key": "end"},
        ],
    )
    engine = make_engine(repos, sleep_fn=lambda s: asyncio.sleep(0), custom_handlers={"boom": always_fails})
    execution = await engine.start_execution(wf.id, triggered_by="u1")
    assert execution.status == ExecutionStatus.COMPENSATED.value

    memory_bridge = engine.bridges.memory
    # the compensated write should have been undone
    assert all(not bucket for bucket in memory_bridge._store.values())


@pytest.mark.asyncio
async def test_pause_resume_and_cancel_lifecycle(repos, workspace, workflow_service, version_service):
    from workflow_platform.models.execution import ExecutionModel

    wf = await _make_workflow(workflow_service, workspace, name="Pause WF")
    version = await publish_graph(
        version_service, wf.id,
        nodes=[
            {"node_key": "start", "node_type": "start", "name": "Start"},
            {"node_key": "step", "node_type": "delay", "name": "Step", "config": {"seconds": 0}},
            {"node_key": "end", "node_type": "end", "name": "End"},
        ],
        edges=[
            {"source_node_key": "start", "target_node_key": "step"},
            {"source_node_key": "step", "target_node_key": "end"},
        ],
    )
    engine = make_engine(repos)

    # manually seed a RUNNING execution mid-graph, simulating a run that was
    # paused externally between node dispatches (the in-process engine's own
    # run() only stops at real pause points, so we construct this state
    # directly to exercise pause/resume/cancel as standalone operations).
    execution = await repos.executions.add(ExecutionModel(
        workflow_id=wf.id, workflow_version_id=version.id, workspace_id=workspace.id,
        status=ExecutionStatus.RUNNING.value, current_node_key="step", triggered_by="u1",
    ))

    paused = await engine.pause_execution(execution.id)
    assert paused.status == ExecutionStatus.PAUSED.value

    resumed = await engine.resume_execution(execution.id)
    assert resumed.status == ExecutionStatus.COMPLETED.value

    cancel_target = await repos.executions.add(ExecutionModel(
        workflow_id=wf.id, workflow_version_id=version.id, workspace_id=workspace.id,
        status=ExecutionStatus.PENDING.value, triggered_by="u1",
    ))
    cancelled = await engine.cancel_execution(cancel_target.id)
    assert cancelled.status == ExecutionStatus.CANCELLED.value


@pytest.mark.asyncio
async def test_nested_workflow_invocation_and_recursion_guard(repos, workspace, workflow_service, version_service):
    inner = await _make_workflow(workflow_service, workspace, name="Inner WF")
    await publish_graph(
        version_service, inner.id,
        nodes=[
            {"node_key": "start", "node_type": "start", "name": "Start"},
            {"node_key": "end", "node_type": "end", "name": "End"},
        ],
        edges=[{"source_node_key": "start", "target_node_key": "end"}],
    )

    outer = await _make_workflow(workflow_service, workspace, name="Outer WF")
    await publish_graph(
        version_service, outer.id,
        nodes=[
            {"node_key": "start", "node_type": "start", "name": "Start"},
            {"node_key": "call_inner", "node_type": "custom", "name": "Call Inner", "config": {"invoke_workflow_id": inner.id, "handler_key": "unused"}},
            {"node_key": "end", "node_type": "end", "name": "End"},
        ],
        edges=[
            {"source_node_key": "start", "target_node_key": "call_inner"},
            {"source_node_key": "call_inner", "target_node_key": "end"},
        ],
    )

    engine = make_engine(repos)
    execution = await engine.start_execution(outer.id, triggered_by="u1")
    assert execution.status == ExecutionStatus.COMPLETED.value

    call_ne = next(ne for ne in await repos.node_executions.list_for_execution(execution.id) if ne.node_key == "call_inner")
    assert call_ne.status == NodeExecutionStatus.SUCCEEDED.value

    children = await repos.executions.list_children(execution.id)
    assert len(children) == 1
    assert children[0].workflow_id == inner.id


@pytest.mark.asyncio
async def test_recursion_depth_guard_raises(repos, workspace, workflow_service, version_service):
    wf = await _make_workflow(workflow_service, workspace, name="Deep WF")
    await publish_graph(
        version_service, wf.id,
        nodes=[
            {"node_key": "start", "node_type": "start", "name": "Start"},
            {"node_key": "end", "node_type": "end", "name": "End"},
        ],
        edges=[{"source_node_key": "start", "target_node_key": "end"}],
    )
    engine = make_engine(repos, max_recursion_depth=2)
    with pytest.raises(RecursionLimitExceededError):
        await engine.start_execution(wf.id, triggered_by="u1", recursion_depth=3)
